import json

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import DifyInterviewTimeoutError, DifyOutputError, DifyTimeoutError
from app.services.dify_interview_service import DifyInterviewService
from app.services.dify_service import DifyService


class _FakeAsyncClient:
    response: httpx.Response | None = None
    error: Exception | None = None
    captured: dict = {}

    def __init__(self, **kwargs):
        self.captured["client_kwargs"] = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        self.captured["url"] = url
        self.captured["request_kwargs"] = kwargs
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def _settings() -> Settings:
    return Settings(
        database_url="sqlite:///:memory:",
        dify_base_url="https://dify.test/v1",
        dify_api_key="analysis-key",
        dify_interview_api_key="interview-key",
    )


def _analysis_payload(*, duplicate: bool = False, related_id: str = "") -> dict:
    return {
        "standard_content": "标准需求",
        "business_goal": "业务目标",
        "type": "NEW_FEATURE",
        "priority": "P2",
        "is_fake": False,
        "fake_reason": "真实需求",
        "is_duplicate": duplicate,
        "related_id": related_id,
        "reference_rule": "RULE-1",
        "analysis_summary": "分析总结",
    }


def _interview_payload() -> dict:
    fields = {
        "target_user": None,
        "usage_scenario": None,
        "user_goal": None,
        "current_problem": None,
        "expected_result": None,
        "proposed_solution": None,
        "frequency": None,
        "impact_scope": None,
        "bug_steps": None,
        "actual_result": None,
        "environment": None,
    }
    return {
        "request_type": "NEW_FEATURE",
        "extracted_fields": fields,
        "next_question": {
            "text": "你在什么场景使用？",
            "target_field": "usage_scenario",
            "reason_code": "MISSING_CORE_FIELD",
        },
        "summary_title": "待澄清需求",
        "validation_ok": True,
        "validation_errors": [],
    }


@pytest.mark.asyncio
async def test_dify_requirement_service_posts_contract_and_parses_nested_result(monkeypatch):
    request = httpx.Request("POST", "https://dify.test/v1/workflows/run")
    _FakeAsyncClient.error = None
    _FakeAsyncClient.captured = {}
    _FakeAsyncClient.response = httpx.Response(
        200,
        json={
            "workflow_run_id": "workflow-1",
            "data": {"status": "succeeded", "outputs": {"result": json.dumps(_analysis_payload())}},
        },
        request=request,
    )
    monkeypatch.setattr("app.services.dify_service.httpx.AsyncClient", _FakeAsyncClient)

    result = await DifyService(_settings()).analyze_requirement(
        project_name="项目",
        project_context="背景",
        raw_content="需求",
        candidates=[{"id": "c" * 32, "standard_content": "候选"}],
        user="tester",
    )

    sent = _FakeAsyncClient.captured["request_kwargs"]["json"]
    assert sent["response_mode"] == "blocking"
    assert sent["user"] == "tester"
    assert json.loads(sent["inputs"]["candidate_requirements"])[0]["id"] == "c" * 32
    assert result.workflow_run_id == "workflow-1"
    assert result.analysis.priority == "P2"


@pytest.mark.asyncio
async def test_dify_requirement_service_rejects_related_id_outside_candidates(monkeypatch):
    request = httpx.Request("POST", "https://dify.test/v1/workflows/run")
    _FakeAsyncClient.error = None
    _FakeAsyncClient.response = httpx.Response(
        200,
        json={
            "data": {
                "status": "succeeded",
                "outputs": _analysis_payload(duplicate=True, related_id="x" * 32),
            }
        },
        request=request,
    )
    monkeypatch.setattr("app.services.dify_service.httpx.AsyncClient", _FakeAsyncClient)

    with pytest.raises(DifyOutputError) as exc_info:
        await DifyService(_settings()).analyze_requirement(
            project_name="项目",
            project_context="背景",
            raw_content="需求",
            candidates=[{"id": "c" * 32, "standard_content": "候选"}],
            user="tester",
        )
    assert exc_info.value.details == "related_id 不在当前项目候选需求中"


@pytest.mark.asyncio
async def test_dify_requirement_timeout_is_mapped(monkeypatch):
    request = httpx.Request("POST", "https://dify.test/v1/workflows/run")
    _FakeAsyncClient.response = None
    _FakeAsyncClient.error = httpx.ReadTimeout("timeout", request=request)
    monkeypatch.setattr("app.services.dify_service.httpx.AsyncClient", _FakeAsyncClient)

    with pytest.raises(DifyTimeoutError):
        await DifyService(_settings()).analyze_requirement(
            project_name="项目",
            project_context="背景",
            raw_content="需求",
            candidates=[],
            user="tester",
        )
    _FakeAsyncClient.error = None


@pytest.mark.asyncio
async def test_dify_interview_service_posts_contract_and_parses_result(monkeypatch):
    request = httpx.Request("POST", "https://dify.test/v1/workflows/run")
    _FakeAsyncClient.error = None
    _FakeAsyncClient.captured = {}
    _FakeAsyncClient.response = httpx.Response(
        200,
        json={
            "workflow_run_id": "interview-workflow-1",
            "data": {
                "status": "succeeded",
                "outputs": {"result": json.dumps(_interview_payload(), ensure_ascii=False)},
            },
        },
        request=request,
    )
    monkeypatch.setattr(
        "app.services.dify_interview_service.httpx.AsyncClient", _FakeAsyncClient
    )

    result = await DifyInterviewService(_settings()).run_turn(
        session_id="session-1",
        project_name="项目",
        project_context="背景",
        raw_content="需求",
        messages=[{"id": "message-1", "role": "USER", "content": "需求"}],
        current_fields={},
        skipped_fields=[],
        latest_message_id="message-1",
        latest_action="INITIAL",
        current_round=0,
        source_channel="MANAGEMENT_WEB",
        images=[],
    )

    sent = _FakeAsyncClient.captured["request_kwargs"]["json"]
    assert sent["user"] == "interview:session-1"
    assert json.loads(sent["inputs"]["messages_json"])[0]["id"] == "message-1"
    assert result.workflow_run_id == "interview-workflow-1"
    assert result.interview.next_question is not None
    assert result.interview.next_question.target_field == "usage_scenario"


@pytest.mark.asyncio
async def test_dify_interview_timeout_is_mapped(monkeypatch):
    request = httpx.Request("POST", "https://dify.test/v1/workflows/run")
    _FakeAsyncClient.response = None
    _FakeAsyncClient.error = httpx.ReadTimeout("timeout", request=request)
    monkeypatch.setattr(
        "app.services.dify_interview_service.httpx.AsyncClient", _FakeAsyncClient
    )

    with pytest.raises(DifyInterviewTimeoutError):
        await DifyInterviewService(_settings()).run_turn(
            session_id="session-1",
            project_name="项目",
            project_context="背景",
            raw_content="需求",
            messages=[],
            current_fields={},
            skipped_fields=[],
            latest_message_id="message-1",
            latest_action="INITIAL",
            current_round=0,
            source_channel="MANAGEMENT_WEB",
            images=[],
        )
    _FakeAsyncClient.error = None
