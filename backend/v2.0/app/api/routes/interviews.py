from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.models import AnalysisStatus, InterviewActionType
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.interview import (
    InterviewActionRequest,
    InterviewAttachmentRead,
    InterviewConfirmRequest,
    InterviewConfirmResult,
    InterviewCreate,
    InterviewDraftRead,
    InterviewMessageCreate,
    InterviewSessionRead,
    InterviewSummaryUpdate,
)
from app.services.interview_attachment_service import InterviewAttachmentService
from app.services.interview_service import InterviewService


router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ApiResponse[InterviewSessionRead], status_code=status.HTTP_201_CREATED)
async def create_interview(
    payload: InterviewCreate, request: Request, db: DbSession
) -> ApiResponse[InterviewSessionRead]:
    service = InterviewService(db)
    session = await service.create(payload)
    return ApiResponse(
        message="访谈会话已创建",
        data=service.to_read(session),
        request_id=request.state.request_id,
    )


@router.get("/drafts", response_model=ApiResponse[list[InterviewDraftRead]])
def list_interview_drafts(
    request: Request,
    db: DbSession,
    created_by: Annotated[str | None, Query(max_length=32)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[list[InterviewDraftRead]]:
    sessions = InterviewService(db).drafts(created_by=created_by, limit=limit)
    return ApiResponse(
        data=[InterviewDraftRead.model_validate(item) for item in sessions],
        request_id=request.state.request_id,
    )


@router.post(
    "/attachments",
    response_model=ApiResponse[InterviewAttachmentRead],
    status_code=status.HTTP_201_CREATED,
)
async def upload_interview_attachment(
    request: Request,
    db: DbSession,
    file: UploadFile = File(...),
    uploaded_by: str | None = Form(default=None, max_length=32),
) -> ApiResponse[InterviewAttachmentRead]:
    attachment = await InterviewAttachmentService(db).upload(
        file,
        uploaded_by=uploaded_by,
    )
    return ApiResponse(
        message="图片上传成功",
        data=InterviewAttachmentRead.model_validate(attachment),
        request_id=request.state.request_id,
    )


@router.get("/attachments/{attachment_id}/content", response_class=FileResponse)
def preview_interview_attachment(
    attachment_id: str,
    db: DbSession,
) -> FileResponse:
    service = InterviewAttachmentService(db)
    attachment = service.get(attachment_id)
    return FileResponse(
        service.content_path(attachment),
        media_type=attachment.mime_type,
    )


@router.get("/{session_id}", response_model=ApiResponse[InterviewSessionRead])
def get_interview(
    session_id: str, request: Request, db: DbSession
) -> ApiResponse[InterviewSessionRead]:
    service = InterviewService(db)
    return ApiResponse(
        data=service.to_read(service.get(session_id)),
        request_id=request.state.request_id,
    )


@router.post("/{session_id}/messages", response_model=ApiResponse[InterviewSessionRead])
async def answer_interview(
    session_id: str,
    payload: InterviewMessageCreate,
    request: Request,
    db: DbSession,
) -> ApiResponse[InterviewSessionRead]:
    service = InterviewService(db)
    session = await service.answer(session_id, payload)
    return ApiResponse(
        message="消息已保存",
        data=service.to_read(session),
        request_id=request.state.request_id,
    )


@router.post("/{session_id}/actions/skip", response_model=ApiResponse[InterviewSessionRead])
async def skip_interview_question(
    session_id: str,
    payload: InterviewActionRequest,
    request: Request,
    db: DbSession,
) -> ApiResponse[InterviewSessionRead]:
    service = InterviewService(db)
    session = await service.skip_or_unknown(
        session_id, payload, action=InterviewActionType.SKIP
    )
    return ApiResponse(
        message="已跳过当前问题",
        data=service.to_read(session),
        request_id=request.state.request_id,
    )


@router.post("/{session_id}/actions/unknown", response_model=ApiResponse[InterviewSessionRead])
async def mark_interview_unknown(
    session_id: str,
    payload: InterviewActionRequest,
    request: Request,
    db: DbSession,
) -> ApiResponse[InterviewSessionRead]:
    service = InterviewService(db)
    session = await service.skip_or_unknown(
        session_id, payload, action=InterviewActionType.UNKNOWN
    )
    return ApiResponse(
        message="已记录为不清楚",
        data=service.to_read(session),
        request_id=request.state.request_id,
    )


@router.post("/{session_id}/actions/summarize", response_model=ApiResponse[InterviewSessionRead])
def summarize_interview(
    session_id: str, request: Request, db: DbSession
) -> ApiResponse[InterviewSessionRead]:
    service = InterviewService(db)
    session = service.summarize(session_id)
    return ApiResponse(
        message="已按当前信息整理",
        data=service.to_read(session),
        request_id=request.state.request_id,
    )


@router.patch("/{session_id}/summary", response_model=ApiResponse[InterviewSessionRead])
def update_interview_summary(
    session_id: str,
    payload: InterviewSummaryUpdate,
    request: Request,
    db: DbSession,
) -> ApiResponse[InterviewSessionRead]:
    service = InterviewService(db)
    session = service.update_summary(session_id, payload)
    return ApiResponse(
        message="需求总结已更新",
        data=service.to_read(session),
        request_id=request.state.request_id,
    )


@router.post("/{session_id}/confirm", response_model=ApiResponse[InterviewConfirmResult])
async def confirm_interview(
    session_id: str,
    payload: InterviewConfirmRequest,
    request: Request,
    db: DbSession,
) -> ApiResponse[InterviewConfirmResult]:
    service = InterviewService(db)
    session, requirement = await service.confirm(session_id, payload)
    analysis_failed = requirement.analysis_status == AnalysisStatus.FAILED
    return ApiResponse(
        code="AI_ANALYSIS_FAILED" if analysis_failed else "OK",
        message=(
            "需求已创建，但 AI 分析失败，可稍后重试"
            if analysis_failed
            else "需求已确认并完成 AI 分析"
        ),
        data=InterviewConfirmResult(
            session=service.to_read(session),
            requirement=requirement,
        ),
        request_id=request.state.request_id,
    )


@router.post("/{session_id}/abandon", response_model=ApiResponse[InterviewSessionRead])
def abandon_interview(
    session_id: str, request: Request, db: DbSession
) -> ApiResponse[InterviewSessionRead]:
    service = InterviewService(db)
    session = service.abandon(session_id)
    return ApiResponse(
        message="访谈已放弃",
        data=service.to_read(session),
        request_id=request.state.request_id,
    )
