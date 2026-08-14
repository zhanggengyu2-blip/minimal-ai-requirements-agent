from datetime import datetime

from pydantic import Field, field_validator

from app.db.models import AnalysisStatus, RequirementPriority, RequirementType
from app.schemas.common import ORMModel


class RequirementCreate(ORMModel):
    project_id: str = Field(min_length=32, max_length=32)
    raw_content: str = Field(min_length=1, max_length=10000)
    created_by: str | None = Field(default=None, max_length=32)

    @field_validator("raw_content")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("需求内容不能仅包含空白字符")
        return value


class RequirementRead(ORMModel):
    id: str
    project_id: str
    raw_content: str
    interview_session_id: str | None
    clarified_content: str | None
    interview_rounds: int
    completeness_score: int | None
    standard_content: str | None
    business_goal: str | None
    type: RequirementType | None
    priority: RequirementPriority | None
    is_fake: bool | None
    fake_reason: str | None
    is_duplicate: bool | None
    related_id: str
    reference_rule: str | None
    analysis_summary: str | None
    analysis_status: AnalysisStatus
    analysis_error_code: str | None
    analysis_error_message: str | None
    dify_workflow_run_id: str | None
    manual_modify: bool
    created_by: str | None
    created_time: datetime
    updated_time: datetime


class BatchAnalyzeRequest(ORMModel):
    requirement_ids: list[str] = Field(min_length=1, max_length=50)

    @field_validator("requirement_ids")
    @classmethod
    def reject_duplicates(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("requirement_ids 不能重复")
        if any(len(item) != 32 for item in value):
            raise ValueError("需求 ID 格式错误")
        return value


class BatchAnalyzeAccepted(ORMModel):
    task_id: str
    total: int
    status: str = "RESERVED"
    message: str = "批量分析接口已预留，异步任务调度将在下一阶段实现"
