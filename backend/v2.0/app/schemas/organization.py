from datetime import datetime

from pydantic import Field, field_validator

from app.core.security import clean_display_name
from app.db.models import InvitationStatus, UserRole
from app.schemas.common import ORMModel


class DepartmentCreate(ORMModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("部门名称不能仅包含空白字符")
        return value


class DepartmentUpdate(DepartmentCreate):
    pass


class DepartmentRead(ORMModel):
    id: str
    name: str
    user_count: int = 0
    project_count: int = 0
    invitation_count: int = 0
    created_time: datetime
    updated_time: datetime


class InvitationCreate(ORMModel):
    department_id: str = Field(min_length=32, max_length=32)
    intended_user_name: str | None = Field(default=None, max_length=50)

    @field_validator("intended_user_name")
    @classmethod
    def normalize_intended_name(cls, value: str | None) -> str | None:
        value = clean_display_name(value) if value else None
        return value or None


class InvitationRead(ORMModel):
    id: str
    code: str
    department_id: str
    department_name: str
    intended_user_name: str | None
    status: InvitationStatus
    used_by_user_id: str | None
    used_by_user_name: str | None
    created_by: str | None
    created_time: datetime
    used_time: datetime | None
    disabled_time: datetime | None


class UserRead(ORMModel):
    id: str
    department_id: str
    department_name: str
    name: str
    role: UserRole
    created_time: datetime
