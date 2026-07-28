from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DifyAnalysisResult(BaseModel):
    """与 dify-rag/04-Dify固定输出-JSON-Schema.json 保持一致。"""

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

