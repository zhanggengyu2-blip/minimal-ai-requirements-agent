from datetime import date, datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from app.db.models import TaskPriority, TaskStatus
from app.schemas.common import ORMModel


class TaskStatusFilter(StrEnum):
    ALL = "ALL"
    UNFINISHED = "UNFINISHED"
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"


class TaskCreate(ORMModel):
    name: str = Field(min_length=1, max_length=200)
    assignee_id: str = Field(min_length=32, max_length=32)
    status: TaskStatus = TaskStatus.NOT_STARTED
    priority: TaskPriority = TaskPriority.P1
    version_id: str | None = Field(default=None, min_length=32, max_length=32)
    start_date: date | None = None
    due_date: date | None = None
    description: str = Field(default="", max_length=500)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("任务名称不能为空")
        return value

    @model_validator(mode="after")
    def validate_dates(self) -> "TaskCreate":
        if self.start_date and self.due_date and self.due_date < self.start_date:
            raise ValueError("预计完成日期不能早于开始日期")
        return self


class TaskUpdate(ORMModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    assignee_id: str | None = Field(default=None, min_length=32, max_length=32)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    version_id: str | None = Field(default=None, min_length=32, max_length=32)
    start_date: date | None = None
    due_date: date | None = None
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def clean_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("任务名称不能为空")
        return value

    @model_validator(mode="after")
    def require_change_and_validate_dates(self) -> "TaskUpdate":
        if not self.model_fields_set - {"expected_revision"}:
            raise ValueError("至少提供一个要修改的字段")
        for field_name in ("name", "assignee_id", "status", "priority", "description"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} 不能为 null")
        if (
            "start_date" in self.model_fields_set
            and "due_date" in self.model_fields_set
            and self.start_date
            and self.due_date
            and self.due_date < self.start_date
        ):
            raise ValueError("预计完成日期不能早于开始日期")
        return self


class TaskRead(ORMModel):
    id: str
    project_id: str
    assignee_id: str
    version_id: str | None
    name: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    start_date: date | None
    due_date: date | None
    sort_order: int
    revision: int
    created_by: str
    updated_by: str
    created_time: datetime
    updated_time: datetime


class TaskLaneRevision(ORMModel):
    assignee_id: str
    revision: int


class TaskList(ORMModel):
    items: list[TaskRead]
    total: int
    limit: int
    truncated: bool
    lanes: list[TaskLaneRevision]


class TaskLaneOrderRead(ORMModel):
    assignee_id: str
    ordered_task_ids: list[str]
    lane_revision: int


class TaskLaneOrderUpdate(ORMModel):
    expected_lane_revision: int = Field(ge=1)
    ordered_task_ids: list[str]

    @field_validator("ordered_task_ids")
    @classmethod
    def validate_task_ids(cls, value: list[str]) -> list[str]:
        if any(len(task_id) != 32 for task_id in value):
            raise ValueError("任务 ID 必须为 32 位")
        if len(value) != len(set(value)):
            raise ValueError("完整任务顺序不能包含重复 ID")
        return value
