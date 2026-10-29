from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnalysisResult(BaseModel):
    """
    定义 Coo 需求分析的十个必填输出字段，是 Pydantic 数据契约，不负责数据库操作。
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
    def validate_related_id(self) -> "AnalysisResult":
        """
        字段校验通过后，要求重复需求的 related_id 非空，非重复需求的 related_id 为空字符串。
        不符合规则时抛出 ValueError，由 Pydantic 汇总为 ValidationError；通过时返回当前实例。
        """
        if self.is_duplicate and not self.related_id:
            raise ValueError("is_duplicate=true 时 related_id 不能为空")
        if not self.is_duplicate and self.related_id:
            raise ValueError("is_duplicate=false 时 related_id 必须为空字符串")
        return self


