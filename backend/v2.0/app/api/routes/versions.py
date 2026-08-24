from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.version import (
    VersionCompletionImpact,
    VersionCreate,
    VersionDeleteResult,
    VersionList,
    VersionRead,
    VersionUpdate,
)
from app.services.version_service import VersionService


router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/{project_id}/versions", response_model=ApiResponse[VersionList])
def list_versions(
    project_id: str,
    request: Request,
    db: DbSession,
) -> ApiResponse[VersionList]:
    versions = VersionService(db).list(project_id, actor=request.state.current_user)
    return ApiResponse(data=versions, request_id=request.state.request_id)


@router.post(
    "/{project_id}/versions",
    response_model=ApiResponse[VersionRead],
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    project_id: str,
    payload: VersionCreate,
    request: Request,
    db: DbSession,
) -> ApiResponse[VersionRead]:
    version = VersionService(db).create(
        project_id,
        payload,
        actor=request.state.current_user,
    )
    return ApiResponse(
        message="版本已创建",
        data=version,
        request_id=request.state.request_id,
    )


@router.get(
    "/{project_id}/versions/{version_id}/completion-impact",
    response_model=ApiResponse[VersionCompletionImpact],
)
def get_version_completion_impact(
    project_id: str,
    version_id: str,
    request: Request,
    db: DbSession,
) -> ApiResponse[VersionCompletionImpact]:
    impact = VersionService(db).completion_impact(
        project_id,
        version_id,
        actor=request.state.current_user,
    )
    return ApiResponse(data=impact, request_id=request.state.request_id)


@router.get("/{project_id}/versions/{version_id}", response_model=ApiResponse[VersionRead])
def get_version(
    project_id: str,
    version_id: str,
    request: Request,
    db: DbSession,
) -> ApiResponse[VersionRead]:
    version = VersionService(db).get(
        project_id,
        version_id,
        actor=request.state.current_user,
    )
    return ApiResponse(data=version, request_id=request.state.request_id)


@router.patch("/{project_id}/versions/{version_id}", response_model=ApiResponse[VersionRead])
def update_version(
    project_id: str,
    version_id: str,
    payload: VersionUpdate,
    request: Request,
    db: DbSession,
) -> ApiResponse[VersionRead]:
    version = VersionService(db).update(
        project_id,
        version_id,
        payload,
        actor=request.state.current_user,
    )
    return ApiResponse(
        message="版本已更新",
        data=version,
        request_id=request.state.request_id,
    )


@router.delete(
    "/{project_id}/versions/{version_id}",
    response_model=ApiResponse[VersionDeleteResult],
)
def delete_version(
    project_id: str,
    version_id: str,
    request: Request,
    db: DbSession,
    expected_revision: Annotated[int, Query(ge=1)],
) -> ApiResponse[VersionDeleteResult]:
    result = VersionService(db).delete(
        project_id,
        version_id,
        expected_revision=expected_revision,
        actor=request.state.current_user,
    )
    return ApiResponse(
        message="版本已删除，相关任务已解除版本关联",
        data=result,
        request_id=request.state.request_id,
    )
