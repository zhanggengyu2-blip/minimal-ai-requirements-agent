from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DifyAnalysisResult(BaseModel):
    """与 product/v1.1/ai/dify-rag/04-Dify固定输出-JSON-Schema.json 保持一致。"""

    model_config = ConfigDict(extra="forbid", strict=True)

    standard_content: str = Field(min_length=1, max_length=4000)
    business_goal: str = Field(min_length=1, max_length=2000)
    type: Literal["NEW_FEATURE", "BUG", "OPTIMIZATION"]
    priority: Literal["P0", "P1", "P2", "P3"]
    is_fake: bool
    fake_reason: str = Field(min_length=1, max_length=2000)
    is_duplicate: bool
    related_id: str = Field(max_length=32)
    reference_rule: str = Field(min_length=1, max_length=2000)
    analysis_summary: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_related_id(self) -> "DifyAnalysisResult":
        if self.is_duplicate and not self.related_id:
            raise ValueError("is_duplicate=true 时 related_id 不能为空")
        if not self.is_duplicate and self.related_id:
            raise ValueError("is_duplicate=false 时 related_id 必须为空字符串")
        return self


InterviewFieldName: TypeAlias = Literal[
    "target_user",
    "usage_scenario",
    "user_goal",
    "current_problem",
    "expected_result",
    "proposed_solution",
    "frequency",
    "impact_scope",
    "bug_steps",
    "actual_result",
    "environment",
]


class DifyInterviewField(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    value: str = Field(min_length=1, max_length=2000)
    evidence_message_ids: list[str] = Field(max_length=20)
    source: Literal["USER_INPUT", "USER_EDIT"]


class DifyInterviewFields(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    target_user: DifyInterviewField | None
    usage_scenario: DifyInterviewField | None
    user_goal: DifyInterviewField | None
    current_problem: DifyInterviewField | None
    expected_result: DifyInterviewField | None
    proposed_solution: DifyInterviewField | None
    frequency: DifyInterviewField | None
    impact_scope: DifyInterviewField | None
    bug_steps: DifyInterviewField | None
    actual_result: DifyInterviewField | None
    environment: DifyInterviewField | None


class DifyInterviewQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    text: str = Field(min_length=1, max_length=120)
    target_field: InterviewFieldName
    reason_code: Literal[
        "MISSING_CORE_FIELD",
        "MISSING_BUG_FIELD",
        "CLARIFY_CONFLICT",
        "SEPARATE_PROBLEM_FROM_SOLUTION",
        "CLARIFY_MULTIPLE_REQUESTS",
        "MISSING_RECOMMENDED_FIELD",
    ]


class DifyInterviewResult(BaseModel):
    """V2.0 访谈 Workflow 固定输出。"""

    model_config = ConfigDict(extra="forbid", strict=True)

    request_type: Literal["NEW_FEATURE", "BUG", "OPTIMIZATION"] | None
    extracted_fields: DifyInterviewFields
    next_question: DifyInterviewQuestion | None
    summary_title: str = Field(min_length=1, max_length=100)
    validation_ok: bool = True
    validation_errors: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def reject_invalid_workflow_result(self) -> "DifyInterviewResult":
        if not self.validation_ok:
            raise ValueError(
                f"Dify 访谈校验失败: {'; '.join(self.validation_errors)[:500]}"
            )
        return self
