import secrets
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.db.models import (
    Department,
    DepartmentStatus,
    InvitationCode,
    InvitationStatus,
    Project,
)
from app.schemas.organization import (
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
    InvitationCreate,
    InvitationRead,
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
        department = self.db.get(Department, department_id)
        if department is None:
            raise NotFoundError("部门不存在")
        values = payload.model_dump(exclude_none=True)
        for key, value in values.items():
            setattr(department, key, value)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("部门名称已存在") from exc
        self.db.refresh(department)
        return self._to_read(department)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        keyword: str | None,
        status: DepartmentStatus | None,
    ) -> tuple[list[DepartmentRead], int]:
        filters = []
        if keyword:
            filters.append(Department.name.ilike(f"%{keyword}%"))
        if status:
            filters.append(Department.status == status)
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

    def _to_read(self, department: Department) -> DepartmentRead:
        project_count = self.db.scalar(
            select(func.count()).select_from(Project).where(Project.department_id == department.id)
        ) or 0
        item = DepartmentRead.model_validate(department)
        item.project_count = project_count
        return item


class InvitationService:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: InvitationCreate) -> InvitationRead:
        department = self.db.get(Department, payload.department_id)
        if department is None:
            raise NotFoundError("部门不存在")
        if department.status != DepartmentStatus.ACTIVE:
            raise ConflictError("停用部门不能生成邀请码")
        invitation = InvitationCode(
            code=self._unique_code(),
            department_id=payload.department_id,
            user_name=payload.user_name,
        )
        self.db.add(invitation)
        self.db.commit()
        self.db.refresh(invitation)
        return self._to_read(invitation)

    def disable(self, invitation_id: str) -> InvitationRead:
        invitation = self.db.get(InvitationCode, invitation_id)
        if invitation is None:
            raise NotFoundError("邀请码不存在")
        if invitation.status == InvitationStatus.USED:
            raise ConflictError("已使用的邀请码不能停用")
        invitation.status = InvitationStatus.DISABLED
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
            filters.append(or_(InvitationCode.code.ilike(f"%{keyword}%"), InvitationCode.user_name.ilike(f"%{keyword}%")))
        if department_id:
            filters.append(InvitationCode.department_id == department_id)
        if status:
            filters.append(InvitationCode.status == status)
        total = self.db.scalar(select(func.count()).select_from(InvitationCode).where(*filters)) or 0
        rows = list(
            self.db.scalars(
                select(InvitationCode)
                .where(*filters)
                .order_by(InvitationCode.created_time.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return [self._to_read(item) for item in rows], total

    def _unique_code(self) -> str:
        while True:
            raw = "".join(secrets.choice(self.alphabet) for _ in range(8))
            code = f"{raw[:4]}-{raw[4:]}"
            if self.db.scalar(select(InvitationCode.id).where(InvitationCode.code == code)) is None:
                return code

    @staticmethod
    def _to_read(invitation: InvitationCode) -> InvitationRead:
        return InvitationRead.model_validate(
            {**invitation.__dict__, "department_name": invitation.department.name}
        )
