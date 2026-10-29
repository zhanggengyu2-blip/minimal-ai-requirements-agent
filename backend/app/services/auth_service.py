from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, AuthenticationError, ConflictError
from app.core.security import (
    csrf_token,
    invitation_digest,
    normalize_name,
    session_digest,
    shared_password_matches,
    generate_session_token,
)
from app.db.models import (
    AuthSession,
    Department,
    InvitationCode,
    InvitationStatus,
    UserAccount,
    UserRole,
    utc_now,
)
from app.schemas.auth import RegistrationRequest, SessionCreateRequest


@dataclass(frozen=True)
class IssuedSession:
    user: UserAccount
    session: AuthSession
    raw_token: str
    csrf_token: str


@dataclass(frozen=True)
class AuthContext:
    user: UserAccount
    session: AuthSession
    raw_token: str
    csrf_token: str


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class AuthService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def register(self, payload: RegistrationRequest) -> IssuedSession:
        code = payload.invitation_code.get_secret_value().strip().upper()
        invitation = self.db.scalar(
            select(InvitationCode).where(
                InvitationCode.code_digest == invitation_digest(code, self.settings)
            )
        )
        if invitation is None or invitation.status == InvitationStatus.DISABLED:
            raise AppError(
                "邀请码无效",
                code="AUTH_INVALID_CREDENTIALS",
                status_code=401,
            )
        if invitation.status == InvitationStatus.USED:
            raise AppError("邀请码已被使用", code="AUTH_INVITATION_USED", status_code=409)

        normalized_name = normalize_name(payload.name)
        intended_name = (
            normalize_name(invitation.intended_user_name)
            if invitation.intended_user_name
            else None
        )
        if invitation.department_id != payload.department_id or (
            intended_name is not None and intended_name != normalized_name
        ):
            raise AppError(
                "部门、姓名或邀请码不匹配",
                code="AUTH_INVALID_CREDENTIALS",
                status_code=401,
            )
        if self._find_user(payload.department_id, normalized_name) is not None:
            raise AppError(
                "该部门下已存在同名用户",
                code="AUTH_NAME_ALREADY_REGISTERED",
                status_code=409,
            )

        user = UserAccount(
            department_id=payload.department_id,
            name=payload.name,
            normalized_name=normalized_name,
            role=UserRole.MEMBER,
            invitation_id=invitation.id,
        )
        self.db.add(user)
        try:
            self.db.flush()
            consumed = self.db.execute(
                update(InvitationCode)
                .where(
                    InvitationCode.id == invitation.id,
                    InvitationCode.status == InvitationStatus.UNUSED,
                )
                .values(
                    status=InvitationStatus.USED,
                    used_by_user_id=user.id,
                    used_time=utc_now(),
                )
            )
            if consumed.rowcount != 1:
                self.db.rollback()
                raise AppError("邀请码已被使用", code="AUTH_INVITATION_USED", status_code=409)
            issued = self._issue_session(user)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            latest_invitation = self.db.get(InvitationCode, invitation.id)
            if latest_invitation is not None and latest_invitation.status == InvitationStatus.USED:
                raise AppError(
                    "邀请码已被使用", code="AUTH_INVITATION_USED", status_code=409
                ) from exc
            raise AppError(
                "该部门下已存在同名用户",
                code="AUTH_NAME_ALREADY_REGISTERED",
                status_code=409,
            ) from exc
        self.db.refresh(user)
        return issued

    def login(self, payload: SessionCreateRequest) -> IssuedSession:
        password = payload.shared_password.get_secret_value()
        user = self._find_user(payload.department_id, normalize_name(payload.name))
        if user is None or not shared_password_matches(password, self.settings):
            raise AppError(
                "部门、姓名或密码不匹配",
                code="AUTH_IDENTITY_MISMATCH",
                status_code=401,
            )
        issued = self._issue_session(user)
        self.db.commit()
        self.db.refresh(user)
        return issued

    def resolve_session(self, raw_token: str) -> AuthContext:
        session = self.db.scalar(
            select(AuthSession)
            .options(joinedload(AuthSession.user).joinedload(UserAccount.department))
            .where(AuthSession.token_digest == session_digest(raw_token, self.settings))
        )
        now = utc_now()
        if (
            session is None
            or session.revoked_time is not None
            or _aware(session.idle_expires_time) <= now
            or _aware(session.absolute_expires_time) <= now
        ):
            raise AuthenticationError()

        session.last_seen_time = now
        session.idle_expires_time = min(
            now + timedelta(days=self.settings.session_idle_days),
            _aware(session.absolute_expires_time),
        )
        self.db.commit()
        return AuthContext(
            user=session.user,
            session=session,
            raw_token=raw_token,
            csrf_token=csrf_token(raw_token, self.settings),
        )

    def revoke(self, session: AuthSession) -> None:
        if session.revoked_time is None:
            session.revoked_time = utc_now()
            self.db.commit()

    def bootstrap_admin(self, *, department_name: str, user_name: str) -> UserAccount:
        department_name = department_name.strip()
        user_name = user_name.strip()
        if not department_name or not user_name:
            raise AppError("部门和管理员姓名不能为空", code="VALIDATION_ERROR", status_code=422)
        admin_count = self.db.scalar(
            select(func.count()).select_from(UserAccount).where(UserAccount.role == UserRole.ADMIN)
        )
        if admin_count:
            raise ConflictError("首个管理员已经存在")

        department = self.db.scalar(select(Department).where(Department.name == department_name))
        if department is None:
            department = Department(name=department_name)
            self.db.add(department)
            self.db.flush()
        normalized_name = normalize_name(user_name)
        if self._find_user(department.id, normalized_name) is not None:
            raise ConflictError("该部门下已存在同名用户")

        user = UserAccount(
            department_id=department.id,
            name=user_name,
            normalized_name=normalized_name,
            role=UserRole.ADMIN,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _issue_session(self, user: UserAccount) -> IssuedSession:
        now = utc_now()
        absolute_expires = now + timedelta(days=self.settings.session_absolute_days)
        idle_expires = min(
            now + timedelta(days=self.settings.session_idle_days), absolute_expires
        )
        raw_token = generate_session_token()
        session = AuthSession(
            user_id=user.id,
            token_digest=session_digest(raw_token, self.settings),
            idle_expires_time=idle_expires,
            absolute_expires_time=absolute_expires,
            last_seen_time=now,
        )
        self.db.add(session)
        self.db.flush()
        return IssuedSession(
            user=user,
            session=session,
            raw_token=raw_token,
            csrf_token=csrf_token(raw_token, self.settings),
        )

    def _find_user(self, department_id: str, normalized_name: str) -> UserAccount | None:
        return self.db.scalar(
            select(UserAccount)
            .options(joinedload(UserAccount.department))
            .where(
                UserAccount.department_id == department_id,
                UserAccount.normalized_name == normalized_name,
            )
        )
