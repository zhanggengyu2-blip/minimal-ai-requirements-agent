import pytest
from pydantic import ValidationError

from app.schemas.dify import DifyAnalysisResult


def test_non_duplicate_requires_empty_related_id():
    with pytest.raises(ValidationError):
        DifyAnalysisResult(
            standard_content="标准需求",
            business_goal="业务目标",
            type="BUG",
            priority="P1",
            is_fake=False,
            fake_reason="真实需求",
            is_duplicate=False,
            related_id="a" * 32,
            reference_rule="RULE-1",
            analysis_summary="总结",
        )


def test_unknown_dify_field_is_rejected():
    payload = {
        "standard_content": "标准需求",
        "business_goal": "业务目标",
        "type": "BUG",
        "priority": "P1",
        "is_fake": False,
        "fake_reason": "真实需求",
        "is_duplicate": False,
        "related_id": "",
        "reference_rule": "RULE-1",
        "analysis_summary": "总结",
        "unexpected": "not allowed",
    }
    with pytest.raises(ValidationError):
        DifyAnalysisResult.model_validate(payload)
