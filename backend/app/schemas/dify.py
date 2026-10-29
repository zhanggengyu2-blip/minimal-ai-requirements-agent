from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DifyAnalysisResult(BaseModel):
    """
    定义 Dify 需求分析的十个必填输出字段，是 Pydantic 数据契约，不负责数据库操作。
    使用严格类型校验并拒绝额外字段，按字段声明限制文本长度、需求类型和优先级取值。
    字段校验后还会检查重复标记与关联 ID 的一致性；候选需求是否存在不由此 Schema 校验。
    """

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
        """
        字段校验通过后，要求重复需求的 related_id 非空，非重复需求的 related_id 为空字符串。
        不符合规则时抛出 ValueError，由 Pydantic 汇总为 ValidationError；通过时返回当前实例。
        """
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
        """
        字段校验通过后，若 Workflow 标记 validation_ok 为假，则拒绝该访谈结果。
        抛出的 ValueError 携带拼接后最多 500 个字符的校验错误内容，由 Pydantic 汇总为 ValidationError；否则返回当前实例。
        """
        if not self.validation_ok:
            raise ValueError(
                f"Dify 访谈校验失败: {'; '.join(self.validation_errors)[:500]}"
            )
        return self
