import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models import AnalysisStatus, RequirementPriority, RequirementType
from app.db.session import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.requirement import (
    BatchAnalyzeAccepted,
    BatchAnalyzeRequest,
    RequirementCreate,
    RequirementRead,
)
from app.schemas.interview import InterviewSessionRead
from app.services.interview_service import InterviewService
from app.services.requirement_service import RequirementService


router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ApiResponse[RequirementRead], status_code=status.HTTP_201_CREATED)
async def create_requirement(
    payload: RequirementCreate, request: Request, db: DbSession
) -> ApiResponse[RequirementRead]:
    requirement = await RequirementService(db).create_and_analyze(
        payload, created_by=request.state.current_user.id
    )
    if requirement.analysis_status == AnalysisStatus.FAILED:
        return ApiResponse(
            code="AI_ANALYSIS_FAILED",
            message="需求已保存，但 AI 分析失败，可稍后重新分析",
            data=RequirementRead.model_validate(requirement),
            request_id=request.state.request_id,
        )
    return ApiResponse(
        message="需求创建及 AI 分析完成",
        data=RequirementRead.model_validate(requirement),
        request_id=request.state.request_id,
    )


@router.get("", response_model=ApiResponse[PageData[RequirementRead]])
def list_requirements(
    request: Request,
    db: DbSession,
    project_id: Annotated[str | None, Query(min_length=32, max_length=32)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    keyword: Annotated[str | None, Query(max_length=100)] = None,
    priority: RequirementPriority | None = None,
    requirement_type: Annotated[RequirementType | None, Query(alias="type")] = None,
    analysis_status: AnalysisStatus | None = None,
    is_fake: bool | None = None,
) -> ApiResponse[PageData[RequirementRead]]:
    items, total = RequirementService(db).list(
        project_id=project_id,
        page=page,
        page_size=page_size,
        keyword=keyword.strip() if keyword else None,
        priority=priority,
        requirement_type=requirement_type,
        analysis_status=analysis_status,
        is_fake=is_fake,
    )
    return ApiResponse(
        data=PageData(
            items=[RequirementRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        ),
        request_id=request.state.request_id,
    )


@router.get("/{requirement_id}", response_model=ApiResponse[RequirementRead])
def get_requirement(requirement_id: str, request: Request, db: DbSession) -> ApiResponse[RequirementRead]:
    requirement = RequirementService(db).get(requirement_id)
    return ApiResponse(
        data=RequirementRead.model_validate(requirement), request_id=request.state.request_id
    )


@router.get(
    "/{requirement_id}/interview", response_model=ApiResponse[InterviewSessionRead]
)
def get_requirement_interview(
    requirement_id: str, request: Request, db: DbSession
) -> ApiResponse[InterviewSessionRead]:
    requirement = RequirementService(db).get(requirement_id)
    if not requirement.interview_session_id:
        raise NotFoundError("该需求没有关联访谈记录")
    service = InterviewService(db)
    return ApiResponse(
        data=service.to_read(service.get(requirement.interview_session_id)),
        request_id=request.state.request_id,
    )


@router.post(
    "/batch-analyze",
    response_model=ApiResponse[BatchAnalyzeAccepted],
    status_code=status.HTTP_202_ACCEPTED,
)
def reserve_batch_analysis(
    payload: BatchAnalyzeRequest, request: Request
) -> ApiResponse[BatchAnalyzeAccepted]:
    data = BatchAnalyzeAccepted(task_id=uuid.uuid4().hex, total=len(payload.requirement_ids))
    return ApiResponse(
        code="ACCEPTED",
        message="批量 AI 分析接口已预留",
        data=data,
        request_id=request.state.request_id,
    )
