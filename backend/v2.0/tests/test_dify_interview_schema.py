import json

import pytest
from pydantic import ValidationError

from app.schemas.dify import DifyInterviewResult
from app.services.dify_interview_service import DifyInterviewService


def _fields():
    return {
        "target_user": None,
        "usage_scenario": None,
        "user_goal": None,
        "current_problem": None,
        "expected_result": None,
        "proposed_solution": {
            "value": "支持批量导出",
            "evidence_message_ids": ["msg-1"],
            "source": "USER_INPUT",
        },
        "frequency": None,
        "impact_scope": None,
        "bug_steps": None,
        "actual_result": None,
        "environment": None,
    }


def test_interview_outputs_accept_dify_json_strings():
    outputs = {
        "request_type": "NEW_FEATURE",
        "extracted_fields": json.dumps(_fields(), ensure_ascii=False),
        "next_question": json.dumps(
            {
                "text": "你通常在什么情况下需要导出？",
                "target_field": "usage_scenario",
                "reason_code": "MISSING_CORE_FIELD",
            },
            ensure_ascii=False,
        ),
        "summary_title": "批量导出",
        "validation_ok": True,
        "validation_errors": "[]",
    }
    normalized = DifyInterviewService._extract_interview(outputs)
    result = DifyInterviewResult.model_validate(normalized)
    assert result.next_question is not None
    assert result.next_question.target_field == "usage_scenario"


def test_interview_validation_ok_false_is_rejected():
    payload = {
        "request_type": None,
        "extracted_fields": _fields(),
        "next_question": None,
        "summary_title": "待整理需求",
        "validation_ok": False,
        "validation_errors": ["证据 ID 非法"],
    }
    with pytest.raises(ValidationError):
        DifyInterviewResult.model_validate(payload)
