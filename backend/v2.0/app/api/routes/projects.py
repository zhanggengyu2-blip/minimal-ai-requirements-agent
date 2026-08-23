from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.db.models import ProjectStatus
from app.db.session import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberList,
    ProjectMembersUpdate,
    ProjectRead,
    ProjectUpdate,
)
from app.services.project_service import ProjectService


router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ApiResponse[ProjectRead], status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, request: Request, db: DbSession) -> ApiResponse[ProjectRead]:
    project = ProjectService(db).create(payload, actor=request.state.current_user)
    return ApiResponse(message="项目创建成功", data=project, request_id=request.state.request_id)


@router.get("", response_model=ApiResponse[PageData[ProjectRead]])
def list_projects(
    request: Request,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    project_status: Annotated[ProjectStatus | None, Query(alias="status")] = None,
) -> ApiResponse[PageData[ProjectRead]]:
    items, total = ProjectService(db).list(
        actor=request.state.current_user,
        page=page,
        page_size=page_size,
        status=project_status.value if project_status else None,
    )
    return ApiResponse(
        data=PageData(items=items, total=total, page=page, page_size=page_size),
        request_id=request.state.request_id,
    )


@router.get("/{project_id}", response_model=ApiResponse[ProjectRead])
def get_project(project_id: str, request: Request, db: DbSession) -> ApiResponse[ProjectRead]:
    project = ProjectService(db).get(project_id, actor=request.state.current_user)
    return ApiResponse(data=project, request_id=request.state.request_id)


@router.patch("/{project_id}", response_model=ApiResponse[ProjectRead])
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    request: Request,
    db: DbSession,
) -> ApiResponse[ProjectRead]:
    project = ProjectService(db).update(
        project_id, payload, actor=request.state.current_user
    )
    return ApiResponse(message="项目已更新", data=project, request_id=request.state.request_id)


@router.get("/{project_id}/members", response_model=ApiResponse[ProjectMemberList])
def list_project_members(
    project_id: str, request: Request, db: DbSession
) -> ApiResponse[ProjectMemberList]:
    members = ProjectService(db).list_members(project_id, actor=request.state.current_user)
    return ApiResponse(data=members, request_id=request.state.request_id)


@router.put("/{project_id}/members", response_model=ApiResponse[ProjectMemberList])
def save_project_members(
    project_id: str,
    payload: ProjectMembersUpdate,
    request: Request,
    db: DbSession,
) -> ApiResponse[ProjectMemberList]:
    members = ProjectService(db).save_members(
        project_id, payload, actor=request.state.current_user
    )
    return ApiResponse(message="项目成员已更新", data=members, request_id=request.state.request_id)
