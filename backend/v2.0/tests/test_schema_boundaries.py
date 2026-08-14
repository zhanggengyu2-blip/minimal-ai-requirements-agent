from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.dify import (
    DifyAnalysisResult,
    DifyInterviewField,
    DifyInterviewFields,
    DifyInterviewQuestion,
)
from app.schemas.interview import (
    InterviewCreate,
    InterviewMessageCreate,
    InterviewSummaryUpdate,
)
from app.schemas.organization import DepartmentCreate, InvitationCreate, InvitationRead
from app.schemas.project import ProjectCreate
from app.schemas.requirement import BatchAnalyzeRequest, RequirementCreate


def test_create_schemas_strip_business_text():
    project = ProjectCreate(name="  项目 A  ", project_context="  项目背景  ")
    department = DepartmentCreate(name="  产品部  ")
    requirement = RequirementCreate(project_id="p" * 32, raw_content="  新需求  ")

    assert project.name == "项目 A"
    assert project.project_context == "项目背景"
    assert department.name == "产品部"
    assert requirement.raw_content == "新需求"


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (ProjectCreate, {"name": "   ", "project_context": "背景"}),
        (ProjectCreate, {"name": "项目", "project_context": "   "}),
        (DepartmentCreate, {"name": "   "}),
        (RequirementCreate, {"project_id": "p" * 32, "raw_content": "   "}),
    ],
)
def test_create_schemas_reject_blank_required_text(schema, payload):
    with pytest.raises(ValidationError):
        schema.model_validate(payload)


@pytest.mark.parametrize("schema", [InterviewCreate, InterviewMessageCreate])
def test_interview_input_requires_text_or_image(schema):
    payload = {"client_message_id": "message-1", "attachment_ids": [], "raw_content": "   "}
    if schema is InterviewCreate:
        payload["project_id"] = "p" * 32
    else:
        payload["content"] = payload.pop("raw_content")

    with pytest.raises(ValidationError):
        schema.model_validate(payload)


@pytest.mark.parametrize("schema", [InterviewCreate, InterviewMessageCreate])
def test_interview_input_rejects_duplicate_or_malformed_attachment_ids(schema):
    base = {"client_message_id": "message-1"}
    if schema is InterviewCreate:
        base["project_id"] = "p" * 32

    with pytest.raises(ValidationError):
        schema.model_validate({**base, "attachment_ids": ["a" * 32, "a" * 32]})
    with pytest.raises(ValidationError):
        schema.model_validate({**base, "attachment_ids": ["short"]})


def test_batch_analyze_rejects_empty_duplicate_malformed_and_oversized_lists():
    with pytest.raises(ValidationError):
        BatchAnalyzeRequest(requirement_ids=[])
    with pytest.raises(ValidationError):
        BatchAnalyzeRequest(requirement_ids=["a" * 32, "a" * 32])
    with pytest.raises(ValidationError):
        BatchAnalyzeRequest(requirement_ids=["short"])
    with pytest.raises(ValidationError):
        BatchAnalyzeRequest(requirement_ids=[f"{index:032d}" for index in range(51)])


def test_summary_update_normalizes_values_and_rejects_unknown_fields():
    summary = InterviewSummaryUpdate(
        fields={"target_user": "  产品经理  ", "usage_scenario": None},
        summary_title="摘要",
    )
    assert summary.fields == {"target_user": "产品经理", "usage_scenario": None}

    with pytest.raises(ValidationError):
        InterviewSummaryUpdate.model_validate({"fields": {"unknown": "value"}})
    with pytest.raises(ValidationError):
        InterviewSummaryUpdate(fields={"target_user": "   "})


def test_dify_analysis_is_strict_and_duplicate_requires_related_id():
    base = {
        "standard_content": "标准需求",
        "business_goal": "业务目标",
        "type": "BUG",
        "priority": "P1",
        "is_fake": False,
        "fake_reason": "真实需求",
        "is_duplicate": True,
        "related_id": "r" * 32,
        "reference_rule": "RULE-1",
        "analysis_summary": "总结",
    }
    assert DifyAnalysisResult.model_validate(base).related_id == "r" * 32

    with pytest.raises(ValidationError):
        DifyAnalysisResult.model_validate({**base, "related_id": ""})
    with pytest.raises(ValidationError):
        DifyAnalysisResult.model_validate({**base, "priority": "P4"})
    with pytest.raises(ValidationError):
        DifyAnalysisResult.model_validate({**base, "is_fake": 0})


def test_dify_interview_nested_contract_requires_all_fields_and_valid_literals():
    field = DifyInterviewField(
        value="产品经理", evidence_message_ids=["message-1"], source="USER_INPUT"
    )
    with pytest.raises(ValidationError):
        DifyInterviewFields(target_user=field)
    with pytest.raises(ValidationError):
        DifyInterviewQuestion(
            text="问题？", target_field="not_a_field", reason_code="MISSING_CORE_FIELD"
        )


def test_nullable_read_field_is_still_required():
    with pytest.raises(ValidationError):
        InvitationRead(
            id="i" * 32,
            code="ABCD-EFGH",
            department_id="d" * 32,
            department_name="产品部",
            status="UNUSED",
            created_time=datetime.now(UTC),
            used_time=None,
        )


def test_invitation_create_normalizes_empty_user_name():
    invitation = InvitationCreate(department_id="d" * 32, user_name="   ")
    assert invitation.user_name is None
