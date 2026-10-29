from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.db.models import ProjectStatus, UserRole
from app.schemas.common import ORMModel


class ProjectCreate(ORMModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    project_context: str = Field(min_length=1, max_length=10000)
    department_id: str | None = Field(default=None, min_length=32, max_length=32)
    member_ids: list[str] = Field(default_factory=list)

    @field_validator("name", "project_context")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("字段不能仅包含空白字符")
        return value

    @field_validator("member_ids")
    @classmethod
    def validate_member_ids(cls, value: list[str]) -> list[str]:
        if any(len(user_id) != 32 for user_id in value):
            raise ValueError("用户 ID 必须为 32 位")
        if len(value) != len(set(value)):
            raise ValueError("成员列表不能包含重复用户")
        return value


class ProjectRead(ORMModel):
    id: str
    name: str
    description: str
    project_context: str
    department_id: str | None
    created_by: str | None
    status: ProjectStatus
    revision: int
    member_revision: int
    member_count: int = 0
    requirement_count: int = 0
    created_time: datetime
    updated_time: datetime


class ProjectUpdate(ORMModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    project_context: str | None = Field(default=None, min_length=1, max_length=10000)
    department_id: str | None = Field(default=None, min_length=32, max_length=32)
    status: ProjectStatus | None = None

    @field_validator("name", "project_context")
    @classmethod
    def reject_optional_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("字段不能仅包含空白字符")
        return value

    @model_validator(mode="after")
    def require_change(self) -> "ProjectUpdate":
        changed_fields = self.model_fields_set - {"expected_revision"}
        if not changed_fields:
            raise ValueError("至少提供一个要修改的字段")
        return self


class ProjectMemberRead(ORMModel):
    user_id: str
    name: str
    department_id: str
    department_name: str
    role: UserRole
    sort_order: int = Field(ge=1)
    task_count: int = 0
    created_time: datetime


class ProjectMemberList(ORMModel):
    items: list[ProjectMemberRead]
    member_revision: int


class ProjectMembersUpdate(ORMModel):
    user_ids: list[str] = Field(min_length=1)
    expected_member_revision: int = Field(ge=1)

    @field_validator("user_ids")
    @classmethod
    def validate_user_ids(cls, value: list[str]) -> list[str]:
        if any(len(user_id) != 32 for user_id in value):
            raise ValueError("用户 ID 必须为 32 位")
        if len(value) != len(set(value)):
            raise ValueError("成员列表不能包含重复用户")
        return value
