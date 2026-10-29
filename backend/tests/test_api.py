from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.db.models import AnalysisStatus
from app.core.exceptions import DifyTimeoutError
from app.main import app
from app.schemas.dify import DifyAnalysisResult
from app.services.dify_service import DifyWorkflowResult


VALID_ANALYSIS = DifyAnalysisResult(
    standard_content="支持批量导入客户需求，并识别重复数据。",
    business_goal="减少人工录入与核对成本。",
    type="NEW_FEATURE",
    priority="P2",
    is_fake=False,
    fake_reason="存在明确用户、场景与效率价值。",
    is_duplicate=False,
    related_id="",
    reference_rule="TYPE-NEW；PRI-P2；FAKE-NOT",
    analysis_summary="该新增功能可减少人工导入成本，建议按 P2 评估，属于真实且非重复需求。",
)


def test_project_and_requirement_happy_path():
    with TestClient(app) as client:
        project_response = client.post(
            "/api/v1/projects",
            json={
                "name": "测试项目",
                "description": "测试",
                "project_context": "面向研发团队的需求管理工具，当前处于 MVP 阶段。",
            },
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["data"]["id"]

        with patch(
            "app.services.dify_service.DifyService.analyze_requirement",
            new=AsyncMock(return_value=DifyWorkflowResult(VALID_ANALYSIS, "run-1")),
        ):
            response = client.post(
                "/api/v1/requirements",
                json={"project_id": project_id, "raw_content": "希望支持批量导入客户需求", "analyze_with_ai": True},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["code"] == "OK"
        assert body["data"]["analysis_status"] == AnalysisStatus.PENDING.value
        assert body["data"]["analysis_summary"] is None

        list_response = client.get("/api/v1/requirements", params={"project_id": project_id})
        assert list_response.status_code == 200
        assert list_response.json()["data"]["total"] == 1

        detail_response = client.get(f"/api/v1/requirements/{body['data']['id']}")
        assert detail_response.status_code == 200
        assert detail_response.json()["data"]["id"] == body["data"]["id"]
        assert detail_response.json()["data"]["analysis_status"] == AnalysisStatus.ANALYZED.value
        assert detail_response.json()["data"]["analysis_summary"] == VALID_ANALYSIS.analysis_summary


def test_validation_error_uses_standard_response():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/requirements", json={"project_id": "bad", "raw_content": "   "}
        )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["data"] is None


def test_dify_failure_keeps_raw_requirement():
    with TestClient(app) as client:
        project_response = client.post(
            "/api/v1/projects",
            json={
                "name": "AI 失败测试项目",
                "project_context": "用于验证 AI 超时后原始需求仍然持久化。",
            },
        )
        project_id = project_response.json()["data"]["id"]
        with patch(
            "app.services.dify_service.DifyService.analyze_requirement",
            new=AsyncMock(side_effect=DifyTimeoutError()),
        ):
            response = client.post(
                "/api/v1/requirements",
                json={"project_id": project_id, "raw_content": "这条需求会分析超时", "analyze_with_ai": True},
            )

        assert response.status_code == 201
        assert response.json()["code"] == "OK"
        assert response.json()["data"]["analysis_status"] == AnalysisStatus.PENDING.value
        body = client.get(f"/api/v1/requirements/{response.json()['data']['id']}").json()
        assert body["data"]["analysis_status"] == AnalysisStatus.FAILED.value
        assert body["data"]["raw_content"] == "这条需求会分析超时"
        assert body["data"]["standard_content"] is None
        assert body["data"]["analysis_error_code"] == "DIFY_TIMEOUT"


def test_create_defaults_to_saved_without_any_ai_call():
    with TestClient(app) as client:
        project = client.post('/api/v1/projects', json={
            'name': '只保存项目', 'project_context': '不调用 AI',
        }).json()['data']
        mocked = AsyncMock()
        with patch('app.services.dify_service.DifyService.analyze_requirement', new=mocked):
            for extra in [{}, {'analyze_with_ai': False}]:
                response = client.post('/api/v1/requirements', json={
                    'project_id': project['id'], 'raw_content': '只保存原始需求', **extra,
                })
                assert response.status_code == 201
                data = response.json()['data']
                assert data['analysis_status'] == 'NOT_RUN'
                assert data['priority'] is None
                assert data['analysis_error_code'] is None
            mocked.assert_not_awaited()
        assert client.get('/api/v1/requirements', params={'project_id': project['id']}).json()['data']['total'] == 2


def test_background_unexpected_failure_preserves_saved_requirement():
    with TestClient(app) as client:
        project = client.post('/api/v1/projects', json={
            'name': '后台异常项目', 'project_context': '后台异常不破坏保存响应',
        }).json()['data']
        with patch('app.services.dify_service.DifyService.analyze_requirement',
                   new=AsyncMock(side_effect=RuntimeError('test unexpected error'))):
            response = client.post('/api/v1/requirements', json={
                'project_id': project['id'], 'raw_content': '后台异常保留原文', 'analyze_with_ai': True,
            })
        assert response.status_code == 201
        assert response.json()['data']['analysis_status'] == 'PENDING'
        stored = client.get('/api/v1/requirements/' + response.json()['data']['id']).json()['data']
        assert stored['raw_content'] == '后台异常保留原文'
        assert stored['analysis_status'] == 'FAILED'
        assert stored['analysis_error_code'] == 'AI_ANALYSIS_ERROR'
