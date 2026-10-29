from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
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
from app.services.project_service import ProjectService


router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _session_with_access(
    db: Session,
    session_id: str,
    *,
    actor,
    writable: bool,
):
    service = InterviewService(db)
    session = service.get(session_id)
    projects = ProjectService(db)
    if writable:
        projects.require_writable(session.project_id, actor=actor)
    else:
        projects.get_visible(session.project_id, actor=actor)
    return service, session


@router.post("", response_model=ApiResponse[InterviewSessionRead], status_code=status.HTTP_201_CREATED)
async def create_interview(
    payload: InterviewCreate, request: Request, db: DbSession
) -> ApiResponse[InterviewSessionRead]:
    ProjectService(db).require_writable(payload.project_id, actor=request.state.current_user)
    service = InterviewService(db)
    session = await service.create(payload, created_by=request.state.current_user.id)
    return ApiResponse(
        message="访谈会话已创建",
        data=service.to_read(session),
        request_id=request.state.request_id,
    )


@router.get("/drafts", response_model=ApiResponse[list[InterviewDraftRead]])
def list_interview_drafts(
    request: Request,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[list[InterviewDraftRead]]:
    sessions = InterviewService(db).drafts(
        created_by=request.state.current_user.id,
        visible_project_ids=ProjectService(db).visible_project_ids(
            actor=request.state.current_user
        ),
        limit=limit,
    )
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
) -> ApiResponse[InterviewAttachmentRead]:
    attachment = await InterviewAttachmentService(db).upload(
        file,
        uploaded_by=request.state.current_user.id,
    )
    return ApiResponse(
        message="图片上传成功",
        data=InterviewAttachmentRead.model_validate(attachment),
        request_id=request.state.request_id,
    )


@router.get("/attachments/{attachment_id}/content", response_class=FileResponse)
def preview_interview_attachment(
    attachment_id: str,
    request: Request,
    db: DbSession,
) -> FileResponse:
    service = InterviewAttachmentService(db)
    attachment = service.get(attachment_id)
    if attachment.session_id:
        session = InterviewService(db).get(attachment.session_id)
        ProjectService(db).get_visible(session.project_id, actor=request.state.current_user)
    elif attachment.uploaded_by != request.state.current_user.id:
        raise NotFoundError("访谈图片不存在")
    return FileResponse(
        service.content_path(attachment),
        media_type=attachment.mime_type,
    )


@router.get("/{session_id}", response_model=ApiResponse[InterviewSessionRead])
def get_interview(
    session_id: str, request: Request, db: DbSession
) -> ApiResponse[InterviewSessionRead]:
    service, session = _session_with_access(
        db, session_id, actor=request.state.current_user, writable=False
    )
    return ApiResponse(
        data=service.to_read(session),
        request_id=request.state.request_id,
    )


@router.post("/{session_id}/messages", response_model=ApiResponse[InterviewSessionRead])
async def answer_interview(
    session_id: str,
    payload: InterviewMessageCreate,
    request: Request,
    db: DbSession,
) -> ApiResponse[InterviewSessionRead]:
    service, _ = _session_with_access(
        db, session_id, actor=request.state.current_user, writable=True
    )
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
    service, _ = _session_with_access(
        db, session_id, actor=request.state.current_user, writable=True
    )
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
    service, _ = _session_with_access(
        db, session_id, actor=request.state.current_user, writable=True
    )
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
    service, _ = _session_with_access(
        db, session_id, actor=request.state.current_user, writable=True
    )
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
    service, _ = _session_with_access(
        db, session_id, actor=request.state.current_user, writable=True
    )
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
    service, _ = _session_with_access(
        db, session_id, actor=request.state.current_user, writable=True
    )
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
    service, _ = _session_with_access(
        db, session_id, actor=request.state.current_user, writable=True
    )
    session = service.abandon(session_id)
    return ApiResponse(
        message="访谈已放弃",
        data=service.to_read(session),
        request_id=request.state.request_id,
    )
