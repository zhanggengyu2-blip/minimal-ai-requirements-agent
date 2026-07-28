from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.db.models import ProjectStatus
from app.db.session import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.project import ProjectCreate, ProjectRead
from app.services.project_service import ProjectService


router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ApiResponse[ProjectRead], status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, request: Request, db: DbSession) -> ApiResponse[ProjectRead]:
    project = ProjectService(db).create(payload)
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
        page=page, page_size=page_size, status=project_status.value if project_status else None
    )
    return ApiResponse(
        data=PageData(items=items, total=total, page=page, page_size=page_size),
        request_id=request.state.request_id,
    )

