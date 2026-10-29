from datetime import date, datetime

from pydantic import Field, field_validator, model_validator

from app.db.models import UserRole, VersionStatus
from app.schemas.common import ORMModel


def _validate_participant_ids(value: list[str]) -> list[str]:
    if any(len(user_id) != 32 for user_id in value):
        raise ValueError("参与人员 ID 必须为 32 位")
    if len(value) != len(set(value)):
        raise ValueError("参与人员不能重复")
    return value


class VersionCreate(ORMModel):
    name: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    participant_ids: list[str] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("版本名称不能为空")
        return value

    @field_validator("participant_ids")
    @classmethod
    def validate_participants(cls, value: list[str]) -> list[str]:
        return _validate_participant_ids(value)

    @model_validator(mode="after")
    def validate_dates(self) -> "VersionCreate":
        if self.end_date < self.start_date:
            raise ValueError("版本结束日期不能早于开始日期")
        return self


class VersionUpdate(ORMModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    status: VersionStatus | None = None
    participant_ids: list[str] | None = Field(default=None, min_length=1)

    @field_validator("name")
    @classmethod
    def clean_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("版本名称不能为空")
        return value

    @field_validator("participant_ids")
    @classmethod
    def validate_participants(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _validate_participant_ids(value)

    @model_validator(mode="after")
    def require_change(self) -> "VersionUpdate":
        changed_fields = self.model_fields_set - {"expected_revision"}
        if not changed_fields:
            raise ValueError("至少提供一个要修改的字段")
        for field_name in changed_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} 不能为 null")
        return self


class VersionParticipantRead(ORMModel):
    user_id: str
    name: str
    department_id: str
    department_name: str
    role: UserRole
    sort_order: int
    task_count: int = 0
    created_time: datetime


class VersionSummaryRead(ORMModel):
    id: str
    project_id: str
    name: str
    start_date: date
    end_date: date
    status: VersionStatus
    revision: int
    task_count: int = 0
    unfinished_task_count: int = 0
    created_by: str
    updated_by: str
    created_time: datetime
    updated_time: datetime


class VersionRead(VersionSummaryRead):
    participants: list[VersionParticipantRead]


class VersionList(ORMModel):
    items: list[VersionSummaryRead]
    total: int


class VersionCompletionImpact(ORMModel):
    version_id: str
    task_count: int
    unfinished_task_count: int


class VersionDeleteResult(ORMModel):
    unlinked_task_count: int
    next_version_id: str | None
