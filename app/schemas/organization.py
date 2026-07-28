from datetime import datetime

from pydantic import Field, field_validator

from app.db.models import DepartmentStatus, InvitationStatus
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


class DepartmentUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    status: DepartmentStatus | None = None

    @field_validator("name")
    @classmethod
    def reject_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("部门名称不能仅包含空白字符")
        return value


class DepartmentRead(ORMModel):
    id: str
    name: str
    status: DepartmentStatus
    user_count: int = 0
    project_count: int = 0
    created_time: datetime
    updated_time: datetime


class InvitationCreate(ORMModel):
    department_id: str = Field(min_length=32, max_length=32)
    user_name: str | None = Field(default=None, max_length=50)

    @field_validator("user_name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        value = value.strip() if value else None
        return value or None


class InvitationRead(ORMModel):
    id: str
    code: str
    department_id: str
    department_name: str
    user_name: str | None
    status: InvitationStatus
    created_time: datetime
    used_time: datetime | None
