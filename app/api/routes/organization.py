from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.db.models import DepartmentStatus, InvitationStatus
from app.db.session import get_db
from app.schemas.common import ApiResponse, PageData
from app.schemas.organization import (
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
    InvitationCreate,
    InvitationRead,
)
from app.services.organization_service import DepartmentService, InvitationService


departments_router = APIRouter()
invitations_router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@departments_router.post("", response_model=ApiResponse[DepartmentRead], status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate, request: Request, db: DbSession
) -> ApiResponse[DepartmentRead]:
    item = DepartmentService(db).create(payload)
    return ApiResponse(message="部门创建成功", data=item, request_id=request.state.request_id)


@departments_router.get("", response_model=ApiResponse[PageData[DepartmentRead]])
def list_departments(
    request: Request,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    keyword: Annotated[str | None, Query(max_length=100)] = None,
    department_status: Annotated[DepartmentStatus | None, Query(alias="status")] = None,
) -> ApiResponse[PageData[DepartmentRead]]:
    items, total = DepartmentService(db).list(
        page=page, page_size=page_size, keyword=keyword, status=department_status
    )
    return ApiResponse(
        data=PageData(items=items, total=total, page=page, page_size=page_size),
        request_id=request.state.request_id,
    )


@departments_router.patch("/{department_id}", response_model=ApiResponse[DepartmentRead])
def update_department(
    department_id: str,
    payload: DepartmentUpdate,
    request: Request,
    db: DbSession,
) -> ApiResponse[DepartmentRead]:
    item = DepartmentService(db).update(department_id, payload)
    return ApiResponse(message="部门更新成功", data=item, request_id=request.state.request_id)


@invitations_router.post("", response_model=ApiResponse[InvitationRead], status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: InvitationCreate, request: Request, db: DbSession
) -> ApiResponse[InvitationRead]:
    item = InvitationService(db).create(payload)
    return ApiResponse(message="邀请码生成成功", data=item, request_id=request.state.request_id)


@invitations_router.get("", response_model=ApiResponse[PageData[InvitationRead]])
def list_invitations(
    request: Request,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    keyword: Annotated[str | None, Query(max_length=100)] = None,
    department_id: Annotated[str | None, Query(max_length=32)] = None,
    invitation_status: Annotated[InvitationStatus | None, Query(alias="status")] = None,
) -> ApiResponse[PageData[InvitationRead]]:
    items, total = InvitationService(db).list(
        page=page,
        page_size=page_size,
        keyword=keyword,
        department_id=department_id,
        status=invitation_status,
    )
    return ApiResponse(
        data=PageData(items=items, total=total, page=page, page_size=page_size),
        request_id=request.state.request_id,
    )


@invitations_router.post("/{invitation_id}/disable", response_model=ApiResponse[InvitationRead])
def disable_invitation(
    invitation_id: str, request: Request, db: DbSession
) -> ApiResponse[InvitationRead]:
    item = InvitationService(db).disable(invitation_id)
    return ApiResponse(message="邀请码已停用", data=item, request_id=request.state.request_id)
