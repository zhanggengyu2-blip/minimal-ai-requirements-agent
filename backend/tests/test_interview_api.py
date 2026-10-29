import pytest
pytestmark = pytest.mark.skip(reason="V4 已下线访谈 API；保留历史集成测试供恢复时使用")

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.dify import (
    DifyInterviewField,
    DifyInterviewFields,
    DifyInterviewQuestion,
    DifyInterviewResult,
)
from app.services.dify_interview_service import DifyInterviewWorkflowResult
from app.services.dify_service import DifyWorkflowResult
from tests.test_api import VALID_ANALYSIS


def _empty_fields() -> dict[str, None]:
    return {
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


def _field(value: str, message_id: str) -> DifyInterviewField:
    return DifyInterviewField(
        value=value,
        evidence_message_ids=[message_id],
        source="USER_INPUT",
    )


async def _interview_turn(**kwargs):
    latest_id = kwargs["latest_message_id"]
    if kwargs["latest_action"] == "INITIAL":
        values = _empty_fields()
        values["proposed_solution"] = _field("需求池支持批量导出", latest_id)
        result = DifyInterviewResult(
            request_type="NEW_FEATURE",
            extracted_fields=DifyInterviewFields(**values),
            next_question=DifyInterviewQuestion(
                text="你通常在什么情况下需要导出这些需求？",
                target_field="usage_scenario",
                reason_code="SEPARATE_PROBLEM_FROM_SOLUTION",
            ),
            summary_title="需求池批量导出",
        )
        return DifyInterviewWorkflowResult(result, "interview-run-1")

    values = _empty_fields()
    values.update(
        {
            "target_user": _field("产品经理", latest_id),
            "usage_scenario": _field("每周制作产品周报", latest_id),
            "user_goal": _field("汇总本周需求并同步给研发", latest_id),
            "current_problem": _field("目前需要逐条复制，整理耗时", latest_id),
            "expected_result": _field("一次导出本周全部需求", latest_id),
            "proposed_solution": _field("需求池支持批量导出", latest_id),
        }
    )
    result = DifyInterviewResult(
        request_type="NEW_FEATURE",
        extracted_fields=DifyInterviewFields(**values),
        next_question=None,
        summary_title="需求池批量导出",
    )
    return DifyInterviewWorkflowResult(result, "interview-run-2")


def test_interview_to_requirement_happy_path():
    with TestClient(app) as client:
        project_response = client.post(
            "/api/v1/projects",
            json={
                "name": "V2 访谈测试项目",
                "project_context": "面向产品团队的需求管理工具。",
            },
        )
        project_id = project_response.json()["data"]["id"]

        with patch(
            "app.services.dify_interview_service.DifyInterviewService.run_turn",
            new=AsyncMock(side_effect=_interview_turn),
        ):
            create_response = client.post(
                "/api/v1/interviews",
                json={
                    "project_id": project_id,
                    "raw_content": "我希望需求池可以支持批量导出",
                    "created_by": "user-v2",
                    "client_message_id": "client-initial-1",
                },
            )
            assert create_response.status_code == 201
            created = create_response.json()["data"]
            assert created["status"] == "INTERVIEWING"
            assert created["current_question"]["target_field"] == "usage_scenario"
            assert created["current_card"]["proposed_solution"]["value"] == "需求池支持批量导出"
            session_id = created["id"]

            answer_response = client.post(
                f"/api/v1/interviews/{session_id}/messages",
                json={
                    "content": "产品经理每周做周报时需要汇总给研发，现在逐条复制很耗时，希望一次导出。",
                    "client_message_id": "client-answer-1",
                },
            )
            assert answer_response.status_code == 200
            answered = answer_response.json()["data"]
            assert answered["status"] == "CONFIRMING"
            assert answered["completeness_score"] == 100
            assert answered["round_count"] == 1
            assert answered["current_question"] is None

        with patch(
            "app.services.dify_service.DifyService.analyze_requirement",
            new=AsyncMock(return_value=DifyWorkflowResult(VALID_ANALYSIS, "analysis-run-v2")),
        ):
            confirm_response = client.post(
                f"/api/v1/interviews/{session_id}/confirm",
                json={"idempotency_key": "confirm-v2-1"},
            )

        assert confirm_response.status_code == 200
        confirmed = confirm_response.json()["data"]
        assert confirmed["session"]["status"] == "SUBMITTED"
        assert confirmed["requirement"]["raw_content"] == "我希望需求池可以支持批量导出"
        assert confirmed["requirement"]["interview_session_id"] == session_id
        assert "【当前问题】" in confirmed["requirement"]["clarified_content"]
        requirement_id = confirmed["requirement"]["id"]

        interview_response = client.get(
            f"/api/v1/requirements/{requirement_id}/interview"
        )
        assert interview_response.status_code == 200
        assert interview_response.json()["data"]["id"] == session_id


def test_interview_initial_message_is_idempotent():
    with TestClient(app) as client:
        project_response = client.post(
            "/api/v1/projects",
            json={
                "name": "V2 幂等测试项目",
                "project_context": "用于验证首条消息幂等。",
            },
        )
        payload = {
            "project_id": project_response.json()["data"]["id"],
            "raw_content": "需求池希望支持导出",
            "client_message_id": "same-client-initial",
        }
        mocked = AsyncMock(side_effect=_interview_turn)
        with patch(
            "app.services.dify_interview_service.DifyInterviewService.run_turn",
            new=mocked,
        ):
            first = client.post("/api/v1/interviews", json=payload)
            second = client.post("/api/v1/interviews", json=payload)

        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["data"]["id"] == second.json()["data"]["id"]
        assert mocked.await_count == 1


async def _skip_turn(**kwargs):
    values = _empty_fields()
    target = "usage_scenario" if kwargs["latest_action"] == "INITIAL" else "target_user"
    result = DifyInterviewResult(
        request_type="NEW_FEATURE",
        extracted_fields=DifyInterviewFields(**values),
        next_question=DifyInterviewQuestion(
            text=(
                "你通常在什么情况下需要这个功能？"
                if target == "usage_scenario"
                else "主要是谁会使用这个功能？"
            ),
            target_field=target,
            reason_code="MISSING_CORE_FIELD",
        ),
        summary_title="待整理需求",
    )
    return DifyInterviewWorkflowResult(result, "skip-run")


def test_two_consecutive_skips_enter_confirming():
    with TestClient(app) as client:
        project_response = client.post(
            "/api/v1/projects",
            json={
                "name": "V2 跳过测试项目",
                "project_context": "用于验证连续跳过的停止条件。",
            },
        )
        with patch(
            "app.services.dify_interview_service.DifyInterviewService.run_turn",
            new=AsyncMock(side_effect=_skip_turn),
        ) as mocked:
            created = client.post(
                "/api/v1/interviews",
                json={
                    "project_id": project_response.json()["data"]["id"],
                    "raw_content": "我想增加一个新功能",
                    "client_message_id": "skip-initial",
                },
            ).json()["data"]
            session_id = created["id"]
            first_skip = client.post(
                f"/api/v1/interviews/{session_id}/actions/skip",
                json={"client_message_id": "skip-action-1"},
            )
            second_skip = client.post(
                f"/api/v1/interviews/{session_id}/actions/unknown",
                json={"client_message_id": "skip-action-2"},
            )

        assert first_skip.status_code == 200
        assert first_skip.json()["data"]["status"] == "INTERVIEWING"
        assert second_skip.status_code == 200
        assert second_skip.json()["data"]["status"] == "CONFIRMING"
        assert second_skip.json()["data"]["stop_reason"] == "CONSECUTIVE_SKIPS"
        assert mocked.await_count == 2
