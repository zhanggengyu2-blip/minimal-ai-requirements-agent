from datetime import datetime

from pydantic import Field, field_validator

from app.db.models import ProjectStatus
from app.schemas.common import ORMModel


class ProjectCreate(ORMModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    project_context: str = Field(min_length=1, max_length=10000)
    department_id: str | None = Field(default=None, max_length=32)

    @field_validator("name", "project_context")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("字段不能仅包含空白字符")
        return value


class ProjectRead(ORMModel):
    id: str
    name: str
    description: str
    project_context: str
    department_id: str | None
    created_by: str | None
    status: ProjectStatus
    requirement_count: int = 0
    created_time: datetime
    updated_time: datetime
