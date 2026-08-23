import hmac
from typing import Annotated

from fastapi import Depends, Header, Request, Security
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.db.models import UserAccount, UserRole
from app.db.session import get_db
from app.services.auth_service import AuthContext, AuthService


DbSession = Annotated[Session, Depends(get_db)]
session_cookie = APIKeyCookie(
    name=get_settings().session_cookie_name,
    auto_error=False,
    scheme_name="SessionCookie",
    description="登录成功后由服务端设置的 HttpOnly 会话 Cookie",
)


def get_auth_context(
    request: Request,
    db: DbSession,
    raw_token: Annotated[str | None, Security(session_cookie)],
) -> AuthContext:
    settings = get_settings()
    if not raw_token:
        raise AuthenticationError()
    context = AuthService(db, settings).resolve_session(raw_token)
    request.state.current_user = context.user
    request.state.auth_context = context
    return context


def get_current_user(context: Annotated[AuthContext, Depends(get_auth_context)]) -> UserAccount:
    return context.user


def require_authenticated_request(
    request: Request,
    context: Annotated[AuthContext, Depends(get_auth_context)],
    csrf_header: Annotated[
        str | None,
        Header(alias=get_settings().csrf_header_name, include_in_schema=True),
    ] = None,
) -> UserAccount:
    settings = get_settings()
    request.state.current_user = context.user
    request.state.auth_context = context
    if settings.csrf_enabled and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        supplied = csrf_header or ""
        if not supplied or not hmac.compare_digest(supplied, context.csrf_token):
            raise PermissionDeniedError("CSRF 令牌无效")
    return context.user


def require_admin(
    user: Annotated[UserAccount, Depends(require_authenticated_request)],
) -> UserAccount:
    if user.role != UserRole.ADMIN:
        raise PermissionDeniedError()
    return user


CurrentUser = Annotated[UserAccount, Depends(get_current_user)]
AuthenticatedUser = Annotated[UserAccount, Depends(require_authenticated_request)]
AdminUser = Annotated[UserAccount, Depends(require_admin)]
