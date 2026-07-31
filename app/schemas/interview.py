from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from app.db.models import (
    InterviewActionType,
    InterviewMessageRole,
    InterviewStatus,
    ProjectResolveMode,
    RequirementType,
    SourceChannel,
)
from app.schemas.common import ORMModel
from app.schemas.dify import DifyInterviewField, DifyInterviewQuestion, InterviewFieldName
from app.schemas.requirement import RequirementRead


class InterviewCreate(ORMModel):
    project_id: str = Field(min_length=32, max_length=32)
    raw_content: str = Field(min_length=1, max_length=10000)
    created_by: str | None = Field(default=None, max_length=32)
    client_message_id: str = Field(min_length=1, max_length=64)

    @field_validator("raw_content")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("需求内容不能仅包含空白字符")
        return value


class InterviewMessageCreate(ORMModel):
    content: str = Field(min_length=1, max_length=10000)
    client_message_id: str = Field(min_length=1, max_length=64)

    @field_validator("content")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("消息不能仅包含空白字符")
        return value


class InterviewActionRequest(ORMModel):
    client_message_id: str = Field(min_length=1, max_length=64)


class InterviewSummaryUpdate(ORMModel):
    model_config = ConfigDict(extra="forbid")

    fields: dict[InterviewFieldName, str | None] = Field(min_length=1, max_length=11)
    summary_title: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("fields")
    @classmethod
    def normalize_fields(
        cls, value: dict[InterviewFieldName, str | None]
    ) -> dict[InterviewFieldName, str | None]:
        normalized: dict[InterviewFieldName, str | None] = {}
        for key, item in value.items():
            if item is None:
                normalized[key] = None
                continue
            item = item.strip()
            if not item:
                raise ValueError(f"{key} 不能仅包含空白字符")
            if len(item) > 2000:
                raise ValueError(f"{key} 不能超过 2000 个字符")
            normalized[key] = item
        return normalized


class InterviewConfirmRequest(ORMModel):
    idempotency_key: str = Field(min_length=1, max_length=64)


class InterviewMessageRead(ORMModel):
    id: str
    session_id: str
    sequence_no: int
    role: InterviewMessageRole
    content: str
    action_type: InterviewActionType | None
    target_field: str | None
    reason_code: str | None
    client_message_id: str | None
    agent_run_id: str | None
    created_time: datetime


class InterviewSessionRead(ORMModel):
    id: str
    project_id: str
    created_by: str | None
    source_channel: SourceChannel
    project_resolve_mode: ProjectResolveMode
    status: InterviewStatus
    raw_content: str
    request_type: RequirementType | None
    current_card: dict[InterviewFieldName, DifyInterviewField | None]
    skipped_fields: list[InterviewFieldName]
    completeness_score: int
    round_count: int
    consecutive_skip_count: int
    stop_reason: str | None
    summary_title: str | None
    clarified_content: str | None
    requirement_id: str | None
    current_question: DifyInterviewQuestion | None
    messages: list[InterviewMessageRead]
    agent_error_code: str | None
    created_time: datetime
    updated_time: datetime


class InterviewConfirmResult(ORMModel):
    session: InterviewSessionRead
    requirement: RequirementRead


class InterviewDraftRead(ORMModel):
    id: str
    project_id: str
    status: InterviewStatus
    raw_content: str
    summary_title: str | None
    round_count: int
    updated_time: datetime


InterviewActionName = Literal["skip", "unknown", "summarize", "abandon"]
