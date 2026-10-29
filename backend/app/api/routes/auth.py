from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_auth_context, require_authenticated_request
from app.core.config import get_settings
from app.db.models import Department
from app.db.session import get_db
from app.schemas.auth import (
    AuthSessionRead,
    CurrentUserRead,
    DepartmentOption,
    RegistrationRequest,
    SessionCreateRequest,
)
from app.schemas.common import ApiResponse
from app.services.auth_service import AuthContext, AuthService, IssuedSession


router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _user_read(context: AuthContext | IssuedSession) -> CurrentUserRead:
    user = context.user
    return CurrentUserRead(
        id=user.id,
        department_id=user.department_id,
        department_name=user.department.name,
        name=user.name,
        role=user.role,
        created_time=user.created_time,
    )


def _session_read(context: AuthContext | IssuedSession) -> AuthSessionRead:
    return AuthSessionRead(user=_user_read(context), csrf_token=context.csrf_token)


def _set_session_cookie(response: Response, issued: IssuedSession) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=issued.raw_token,
        max_age=settings.session_absolute_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/api/v1",
    )


@router.get("/departments", response_model=ApiResponse[list[DepartmentOption]])
def list_login_departments(request: Request, db: DbSession) -> ApiResponse[list[DepartmentOption]]:
    departments = list(db.scalars(select(Department).order_by(Department.name.asc())))
    return ApiResponse(
        data=[DepartmentOption.model_validate(item) for item in departments],
        request_id=request.state.request_id,
    )


@router.post(
    "/registrations",
    response_model=ApiResponse[AuthSessionRead],
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegistrationRequest,
    request: Request,
    response: Response,
    db: DbSession,
) -> ApiResponse[AuthSessionRead]:
    issued = AuthService(db).register(payload)
    _set_session_cookie(response, issued)
    return ApiResponse(
        message="注册成功",
        data=_session_read(issued),
        request_id=request.state.request_id,
    )


@router.post("/sessions", response_model=ApiResponse[AuthSessionRead])
def login(
    payload: SessionCreateRequest,
    request: Request,
    response: Response,
    db: DbSession,
) -> ApiResponse[AuthSessionRead]:
    issued = AuthService(db).login(payload)
    _set_session_cookie(response, issued)
    return ApiResponse(
        message="登录成功",
        data=_session_read(issued),
        request_id=request.state.request_id,
    )


@router.get("/me", response_model=ApiResponse[AuthSessionRead])
def me(
    request: Request,
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> ApiResponse[AuthSessionRead]:
    return ApiResponse(data=_session_read(context), request_id=request.state.request_id)


@router.delete(
    "/session",
    response_model=ApiResponse[dict[str, bool]],
    dependencies=[Depends(require_authenticated_request)],
)
def logout(
    request: Request,
    response: Response,
    db: DbSession,
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> ApiResponse[dict[str, bool]]:
    AuthService(db).revoke(context.session)
    response.delete_cookie(get_settings().session_cookie_name, path="/api/v1")
    return ApiResponse(
        message="已退出登录",
        data={"revoked": True},
        request_id=request.state.request_id,
    )
