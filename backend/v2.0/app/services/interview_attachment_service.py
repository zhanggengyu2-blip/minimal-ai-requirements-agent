from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, InvalidImageError, NotFoundError
from app.db.models import InterviewAttachment, InterviewMessage, InterviewSession, new_id


ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class InterviewAttachmentService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.storage_dir = Path(self.settings.interview_image_storage_dir).resolve()

    async def upload(
        self,
        file: UploadFile,
        *,
        uploaded_by: str | None,
    ) -> InterviewAttachment:
        original_name = Path(file.filename or "image").name[:255]
        extension = Path(original_name).suffix.lower()
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise InvalidImageError("仅支持 PNG、JPG/JPEG、WEBP 图片")
        if file.content_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise InvalidImageError("图片 Content-Type 不受支持")

        data = bytearray()
        while chunk := await file.read(1024 * 1024):
            data.extend(chunk)
            if len(data) > self.settings.interview_image_max_bytes:
                raise InvalidImageError(
                    "单张图片不能超过 10MB",
                    code="IMAGE_TOO_LARGE",
                    status_code=413,
                )
        if not data:
            raise InvalidImageError("不能上传空图片")

        detected_mime = self._detect_image_mime(bytes(data))
        if detected_mime is None or detected_mime != file.content_type:
            raise InvalidImageError("图片内容与声明格式不一致")

        attachment_id = new_id()
        stored_name = f"{attachment_id}{ALLOWED_IMAGE_MIME_TYPES[detected_mime]}"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        target = self.storage_dir / stored_name
        target.write_bytes(data)

        attachment = InterviewAttachment(
            id=attachment_id,
            uploaded_by=uploaded_by,
            original_name=original_name,
            stored_name=stored_name,
            storage_path=str(target),
            mime_type=detected_mime,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )
        self.db.add(attachment)
        try:
            self.db.commit()
        except Exception:
            target.unlink(missing_ok=True)
            raise
        self.db.refresh(attachment)
        return attachment

    def get(self, attachment_id: str) -> InterviewAttachment:
        attachment = self.db.get(InterviewAttachment, attachment_id)
        if attachment is None:
            raise NotFoundError("访谈图片不存在")
        return attachment

    def content_path(self, attachment: InterviewAttachment) -> Path:
        path = Path(attachment.storage_path).resolve()
        if self.storage_dir not in path.parents or not path.is_file():
            raise NotFoundError("访谈图片文件不存在")
        return path

    def bind_to_message(
        self,
        attachment_ids: list[str],
        *,
        session: InterviewSession,
        message: InterviewMessage,
        uploaded_by: str | None,
    ) -> list[InterviewAttachment]:
        if not attachment_ids:
            return []
        if len(attachment_ids) > self.settings.interview_image_max_count:
            raise InvalidImageError("每次最多关联 5 张图片")

        attachments = list(
            self.db.scalars(
                select(InterviewAttachment).where(InterviewAttachment.id.in_(attachment_ids))
            )
        )
        by_id = {item.id: item for item in attachments}
        missing = [item for item in attachment_ids if item not in by_id]
        if missing:
            raise NotFoundError("存在未找到的访谈图片")

        ordered = [by_id[item] for item in attachment_ids]
        for attachment in ordered:
            if attachment.message_id and attachment.message_id != message.id:
                raise ConflictError("图片已经关联到其他访谈消息")
            if attachment.session_id and attachment.session_id != session.id:
                raise ConflictError("图片已经关联到其他访谈会话")
            if (
                uploaded_by is not None
                and attachment.uploaded_by is not None
                and attachment.uploaded_by != uploaded_by
            ):
                raise ConflictError("不能关联其他用户上传的图片")
            attachment.session = session
            attachment.message = message
        self.db.flush()
        return ordered

    @staticmethod
    def _detect_image_mime(data: bytes) -> str | None:
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "image/webp"
        return None
