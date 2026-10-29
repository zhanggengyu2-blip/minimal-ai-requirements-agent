from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.security import (
    decrypt_invitation,
    encrypt_invitation,
    generate_invitation_code,
    invitation_digest,
)
from app.db.models import (
    Department,
    InvitationCode,
    InvitationStatus,
    Project,
    UserAccount,
    utc_now,
)
from app.schemas.organization import (
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
    InvitationCreate,
    InvitationRead,
    UserRead,
)


class DepartmentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: DepartmentCreate) -> DepartmentRead:
        department = Department(name=payload.name)
        self.db.add(department)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("部门名称已存在") from exc
        self.db.refresh(department)
        return self._to_read(department)

    def update(self, department_id: str, payload: DepartmentUpdate) -> DepartmentRead:
        department = self._get(department_id)
        department.name = payload.name
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("部门名称已存在") from exc
        self.db.refresh(department)
        return self._to_read(department)

    def delete(self, department_id: str) -> None:
        department = self._get(department_id)
        counts = self._reference_counts(department.id)
        if any(counts.values()):
            raise AppError(
                "部门仍被使用，无法删除",
                code="DEPARTMENT_IN_USE",
                status_code=409,
                details=counts,
            )
        self.db.delete(department)
        self.db.commit()

    def list(
        self,
        *,
        page: int,
        page_size: int,
        keyword: str | None,
    ) -> tuple[list[DepartmentRead], int]:
        filters = [Department.name.ilike(f"%{keyword}%")] if keyword else []
        total = self.db.scalar(select(func.count()).select_from(Department).where(*filters)) or 0
        rows = list(
            self.db.scalars(
                select(Department)
                .where(*filters)
                .order_by(Department.created_time.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return [self._to_read(item) for item in rows], total

    def _get(self, department_id: str) -> Department:
        department = self.db.get(Department, department_id)
        if department is None:
            raise NotFoundError("部门不存在")
        return department

    def _reference_counts(self, department_id: str) -> dict[str, int]:
        return {
            "user_count": self.db.scalar(
                select(func.count()).select_from(UserAccount).where(
                    UserAccount.department_id == department_id
                )
            ) or 0,
            "project_count": self.db.scalar(
                select(func.count()).select_from(Project).where(Project.department_id == department_id)
            ) or 0,
            "invitation_count": self.db.scalar(
                select(func.count()).select_from(InvitationCode).where(
                    InvitationCode.department_id == department_id
                )
            ) or 0,
        }

    def _to_read(self, department: Department) -> DepartmentRead:
        return DepartmentRead.model_validate(
            {**department.__dict__, **self._reference_counts(department.id)}
        )


class InvitationService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def create(self, payload: InvitationCreate, *, actor_id: str) -> InvitationRead:
        department = self.db.get(Department, payload.department_id)
        if department is None:
            raise NotFoundError("部门不存在")
        for _ in range(10):
            code = generate_invitation_code()
            invitation = InvitationCode(
                code_digest=invitation_digest(code, self.settings),
                code_ciphertext=encrypt_invitation(code, self.settings),
                department_id=payload.department_id,
                intended_user_name=payload.intended_user_name,
                created_by=actor_id,
            )
            self.db.add(invitation)
            try:
                self.db.commit()
            except IntegrityError:
                self.db.rollback()
                continue
            self.db.refresh(invitation)
            return self._to_read(invitation)
        raise ConflictError("邀请码生成冲突，请重试")

    def disable(self, invitation_id: str) -> InvitationRead:
        invitation = self._get(invitation_id)
        if invitation.status == InvitationStatus.USED:
            raise ConflictError("已使用的邀请码不能停用")
        if invitation.status != InvitationStatus.DISABLED:
            invitation.status = InvitationStatus.DISABLED
            invitation.disabled_time = utc_now()
            self.db.commit()
            self.db.refresh(invitation)
        return self._to_read(invitation)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        keyword: str | None,
        department_id: str | None,
        status: InvitationStatus | None,
    ) -> tuple[list[InvitationRead], int]:
        filters = []
        if keyword:
            keyword_filters = [InvitationCode.intended_user_name.ilike(f"%{keyword}%")]
            normalized_code = keyword.strip().upper()
            if len(normalized_code) == 9:
                keyword_filters.append(
                    InvitationCode.code_digest == invitation_digest(normalized_code, self.settings)
                )
            filters.append(or_(*keyword_filters))
        if department_id:
            filters.append(InvitationCode.department_id == department_id)
        if status:
            filters.append(InvitationCode.status == status)
        total = self.db.scalar(select(func.count()).select_from(InvitationCode).where(*filters)) or 0
        rows = list(
            self.db.scalars(
                select(InvitationCode)
                .options(joinedload(InvitationCode.department))
                .where(*filters)
                .order_by(InvitationCode.created_time.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return [self._to_read(item) for item in rows], total

    def _get(self, invitation_id: str) -> InvitationCode:
        invitation = self.db.scalar(
            select(InvitationCode)
            .options(joinedload(InvitationCode.department))
            .where(InvitationCode.id == invitation_id)
        )
        if invitation is None:
            raise NotFoundError("邀请码不存在")
        return invitation

    def _to_read(self, invitation: InvitationCode) -> InvitationRead:
        used_by_name = None
        if invitation.used_by_user_id:
            used_by_name = self.db.scalar(
                select(UserAccount.name).where(UserAccount.id == invitation.used_by_user_id)
            )
        return InvitationRead.model_validate(
            {
                **invitation.__dict__,
                "code": decrypt_invitation(invitation.code_ciphertext, self.settings),
                "department_name": invitation.department.name,
                "used_by_user_name": used_by_name,
            }
        )


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        *,
        page: int,
        page_size: int,
        keyword: str | None,
        department_id: str | None,
    ) -> tuple[list[UserRead], int]:
        filters = []
        if keyword:
            filters.append(UserAccount.name.ilike(f"%{keyword}%"))
        if department_id:
            filters.append(UserAccount.department_id == department_id)
        total = self.db.scalar(select(func.count()).select_from(UserAccount).where(*filters)) or 0
        users = list(
            self.db.scalars(
                select(UserAccount)
                .options(joinedload(UserAccount.department))
                .where(*filters)
                .order_by(UserAccount.name.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return [
            UserRead.model_validate({**user.__dict__, "department_name": user.department.name})
            for user in users
        ], total
