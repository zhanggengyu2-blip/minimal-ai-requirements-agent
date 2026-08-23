from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.db.models import Department, Requirement
from app.main import app
from app.schemas.dify import DifyAnalysisResult
from app.services.dify_service import DifyWorkflowResult


def _analysis() -> DifyAnalysisResult:
    return DifyAnalysisResult(
        standard_content="标准需求",
        business_goal="降低处理成本",
        type="OPTIMIZATION",
        priority="P2",
        is_fake=False,
        fake_reason="场景明确",
        is_duplicate=False,
        related_id="",
        reference_rule="TYPE-OPT；PRI-P2",
        analysis_summary="建议按 P2 评估。",
    )


def test_request_id_is_echoed_in_success_and_validation_error():
    with TestClient(app) as client:
        success = client.get("/api/v1/projects", headers={"X-Request-ID": "request-success"})
        invalid = client.get(
            "/api/v1/projects",
            params={"page": 0},
            headers={"X-Request-ID": "request-invalid"},
        )

    assert success.status_code == 200
    assert success.headers["X-Request-ID"] == "request-success"
    assert success.json()["request_id"] == "request-success"
    assert invalid.status_code == 422
    assert invalid.headers["X-Request-ID"] == "request-invalid"
    assert invalid.json()["request_id"] == "request-invalid"
    assert invalid.json()["code"] == "VALIDATION_ERROR"


def test_duplicate_project_and_department_return_conflict():
    with TestClient(app) as client:
        project_payload = {"name": "唯一项目", "project_context": "项目背景"}
        assert client.post("/api/v1/projects", json=project_payload).status_code == 201
        project_duplicate = client.post("/api/v1/projects", json=project_payload)

        department_payload = {"name": "唯一部门"}
        assert client.post("/api/v1/departments", json=department_payload).status_code == 201
        department_duplicate = client.post("/api/v1/departments", json=department_payload)

    assert project_duplicate.status_code == 409
    assert project_duplicate.json()["code"] == "CONFLICT"
    assert department_duplicate.status_code == 409
    assert department_duplicate.json()["code"] == "CONFLICT"


def test_not_found_errors_use_standard_response():
    missing_id = "0" * 32
    with TestClient(app) as client:
        requirement = client.get(f"/api/v1/requirements/{missing_id}")
        interview = client.get(f"/api/v1/interviews/{missing_id}")
        invitation = client.post(f"/api/v1/invitations/{missing_id}/disable")

    for response in (requirement, interview, invitation):
        assert response.status_code == 404
        assert response.json()["code"] == "NOT_FOUND"
        assert response.json()["data"] is None
        assert response.json()["request_id"]


def test_requirement_create_rejects_missing_project_without_calling_dify():
    mocked = AsyncMock()
    with patch(
        "app.services.dify_service.DifyService.analyze_requirement",
        new=mocked,
    ):
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/requirements",
                json={"project_id": "f" * 32, "raw_content": "孤立需求"},
            )

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    mocked.assert_not_awaited()


def test_requirement_filters_and_pagination_contract():
    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={"name": "筛选项目", "project_context": "筛选测试"},
        ).json()["data"]
        mocked = AsyncMock(
            return_value=DifyWorkflowResult(analysis=_analysis(), workflow_run_id="filter-run")
        )
        with patch(
            "app.services.dify_service.DifyService.analyze_requirement",
            new=mocked,
        ):
            client.post(
                "/api/v1/requirements",
                json={"project_id": project["id"], "raw_content": "需要优化导出"},
            )

        filtered = client.get(
            "/api/v1/requirements",
            params={
                "project_id": project["id"],
                "type": "OPTIMIZATION",
                "priority": "P2",
                "analysis_status": "ANALYZED",
                "is_fake": "false",
                "keyword": "标准",
                "page": 1,
                "page_size": 1,
            },
        )
        invalid_page = client.get("/api/v1/requirements", params={"page_size": 101})

    assert filtered.status_code == 200
    assert filtered.json()["data"]["total"] == 1
    assert filtered.json()["data"]["page_size"] == 1
    assert filtered.json()["data"]["items"][0]["type"] == "OPTIMIZATION"
    assert invalid_page.status_code == 422


def test_batch_analysis_endpoint_is_explicitly_reserved(db_session):
    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={"name": "批量分析项目", "project_context": "验证批量分析预留接口"},
        ).json()["data"]
        requirements = [
            Requirement(project_id=project["id"], raw_content="需求一"),
            Requirement(project_id=project["id"], raw_content="需求二"),
        ]
        db_session.add_all(requirements)
        db_session.commit()
        ids = [item.id for item in requirements]
        response = client.post("/api/v1/requirements/batch-analyze", json={"requirement_ids": ids})
        duplicate = client.post(
            "/api/v1/requirements/batch-analyze",
            json={"requirement_ids": [ids[0], ids[0]]},
        )

    assert response.status_code == 202
    assert response.json()["code"] == "ACCEPTED"
    assert response.json()["data"]["status"] == "RESERVED"
    assert response.json()["data"]["total"] == 2
    assert duplicate.status_code == 422


def test_department_with_invitation_cannot_be_deleted(db_session):
    department = Department(name="被引用部门")
    db_session.add(department)
    db_session.commit()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/invitations",
            json={"department_id": department.id, "intended_user_name": "测试用户"},
        )
        assert response.status_code == 201
        response = client.delete(f"/api/v1/departments/{department.id}")

    assert response.status_code == 409
    assert response.json()["code"] == "DEPARTMENT_IN_USE"
    assert response.json()["details"]["invitation_count"] == 1


def test_archived_project_cannot_start_interview():
    mocked = AsyncMock()
    with patch(
        "app.services.dify_interview_service.DifyInterviewService.run_turn",
        new=mocked,
    ):
        with TestClient(app) as client:
            project = client.post(
                "/api/v1/projects",
                json={"name": "归档项目", "project_context": "不能创建访谈"},
            ).json()["data"]
            archived = client.patch(
                f"/api/v1/projects/{project['id']}",
                json={"expected_revision": project["revision"], "status": "ARCHIVED"},
            )
            assert archived.status_code == 200
            response = client.post(
                "/api/v1/interviews",
                json={
                    "project_id": project["id"],
                    "raw_content": "归档项目需求",
                    "client_message_id": "archived-project-message",
                },
            )

    assert response.status_code == 403
    assert response.json()["code"] == "PERMISSION_DENIED"
    mocked.assert_not_awaited()


def test_interview_actions_reject_missing_session_and_invalid_summary_field():
    session_id = "0" * 32
    with TestClient(app) as client:
        summarize = client.post(f"/api/v1/interviews/{session_id}/actions/summarize")
        invalid_summary = client.patch(
            f"/api/v1/interviews/{session_id}/summary",
            json={"fields": {"unknown_field": "value"}},
        )

    assert summarize.status_code == 404
    assert summarize.json()["code"] == "NOT_FOUND"
    assert invalid_summary.status_code == 422
    assert invalid_summary.json()["code"] == "VALIDATION_ERROR"
