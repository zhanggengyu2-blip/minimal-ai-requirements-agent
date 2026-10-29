from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.dify import (
    DifyInterviewFields,
    DifyInterviewQuestion,
    DifyInterviewResult,
)
from app.services.dify_interview_service import (
    DifyInterviewService,
    DifyInterviewWorkflowResult,
)


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"test-image-content"


async def _image_turn(**kwargs):
    fields = DifyInterviewFields(
        target_user=None,
        usage_scenario=None,
        user_goal=None,
        current_problem=None,
        expected_result=None,
        proposed_solution=None,
        frequency=None,
        impact_scope=None,
        bug_steps=None,
        actual_result=None,
        environment=None,
    )
    return DifyInterviewWorkflowResult(
        interview=DifyInterviewResult(
            request_type="OPTIMIZATION",
            extracted_fields=fields,
            next_question=DifyInterviewQuestion(
                text="图片中需要调整的是哪个页面位置？",
                target_field="usage_scenario",
                reason_code="MISSING_CORE_FIELD",
            ),
            summary_title="图片需求待确认",
        ),
        workflow_run_id="image-run-1",
        uploaded_file_ids={
            item["attachment_id"]: "dify-upload-1" for item in kwargs["images"]
        },
    )


def _upload_image(client: TestClient, *, uploaded_by: str = "image-user") -> dict:
    response = client.post(
        "/api/v1/interviews/attachments",
        data={"uploaded_by": uploaded_by},
        files={"file": ("position.png", PNG_BYTES, "image/png")},
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_upload_and_create_image_only_interview():
    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={
                "name": "V2 图片访谈项目",
                "project_context": "用于验证图片需求提交。",
            },
        ).json()["data"]
        attachment = _upload_image(client)

        mocked = AsyncMock(side_effect=_image_turn)
        with patch(
            "app.services.dify_interview_service.DifyInterviewService.run_turn",
            new=mocked,
        ):
            response = client.post(
                "/api/v1/interviews",
                json={
                    "project_id": project["id"],
                    "raw_content": "",
                    "created_by": "image-user",
                    "client_message_id": "image-only-initial-001",
                    "attachment_ids": [attachment["id"]],
                },
            )

        assert response.status_code == 201
        session = response.json()["data"]
        message_attachment = session["messages"][0]["attachments"][0]
        assert message_attachment["id"] == attachment["id"]
        assert message_attachment["session_id"] == session["id"]
        assert message_attachment["message_id"] == session["messages"][0]["id"]
        assert message_attachment["preview_url"].endswith(
            f"/{attachment['id']}/content"
        )
        assert mocked.await_args.kwargs["images"][0]["attachment_id"] == attachment["id"]

        preview = client.get(message_attachment["preview_url"])
        assert preview.status_code == 200
        assert preview.headers["content-type"] == "image/png"
        assert preview.content == PNG_BYTES


def test_answer_can_contain_only_image_and_cannot_reuse_bound_image():
    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={
                "name": "V2 图片回答项目",
                "project_context": "用于验证回答携带图片。",
            },
        ).json()["data"]
        with patch(
            "app.services.dify_interview_service.DifyInterviewService.run_turn",
            new=AsyncMock(side_effect=_image_turn),
        ):
            created = client.post(
                "/api/v1/interviews",
                json={
                    "project_id": project["id"],
                    "raw_content": "这个页面位置需要优化",
                    "created_by": "image-user",
                    "client_message_id": "image-answer-initial-001",
                },
            ).json()["data"]
            attachment = _upload_image(client)
            answer = client.post(
                f"/api/v1/interviews/{created['id']}/messages",
                json={
                    "content": "",
                    "client_message_id": "image-answer-001",
                    "attachment_ids": [attachment["id"]],
                },
            )

        assert answer.status_code == 200
        assert answer.json()["data"]["messages"][-2]["attachments"][0]["id"] == attachment["id"]

        other_project = client.post(
            "/api/v1/projects",
            json={
                "name": "V2 图片重复关联项目",
                "project_context": "用于验证图片不能跨会话复用。",
            },
        ).json()["data"]
        conflict = client.post(
            "/api/v1/interviews",
            json={
                "project_id": other_project["id"],
                "raw_content": "复用图片",
                "created_by": "image-user",
                "client_message_id": "image-conflict-initial-001",
                "attachment_ids": [attachment["id"]],
            },
        )
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "CONFLICT"


def test_rejects_fake_image_and_empty_submission():
    with TestClient(app) as client:
        fake = client.post(
            "/api/v1/interviews/attachments",
            files={"file": ("fake.png", b"not-a-png", "image/png")},
        )
        assert fake.status_code == 400
        assert fake.json()["code"] == "INVALID_IMAGE"

        project = client.post(
            "/api/v1/projects",
            json={
                "name": "V2 图片空提交项目",
                "project_context": "用于验证空提交。",
            },
        ).json()["data"]
        empty = client.post(
            "/api/v1/interviews",
            json={
                "project_id": project["id"],
                "raw_content": "   ",
                "client_message_id": "empty-image-initial-001",
                "attachment_ids": [],
            },
        )
        assert empty.status_code == 422
        assert empty.json()["code"] == "VALIDATION_ERROR"


async def test_dify_image_input_uses_uploaded_file_contract(tmp_path):
    image_path = tmp_path / "screen.png"
    image_path.write_bytes(PNG_BYTES)
    service = DifyInterviewService()
    service._upload_image = AsyncMock(return_value="dify-file-id")  # type: ignore[method-assign]

    inputs, uploaded = await service._prepare_images(
        [
            {
                "attachment_id": "a" * 32,
                "path": str(image_path),
                "name": "screen.png",
                "mime_type": "image/png",
                "dify_upload_file_id": None,
                "dify_user": None,
            }
        ],
        user="interview:session-1",
    )

    assert inputs == [
        {
            "type": "image",
            "transfer_method": "local_file",
            "upload_file_id": "dify-file-id",
        }
    ]
    assert uploaded == {"a" * 32: "dify-file-id"}


async def test_dify_upload_uses_same_interview_user(tmp_path, monkeypatch):
    image_path = tmp_path / "screen.png"
    image_path.write_bytes(PNG_BYTES)
    captured = {}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured["data"] = kwargs["data"]
            captured["files"] = kwargs["files"]
            return httpx.Response(
                201,
                json={"id": "dify-upload-id"},
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(
        "app.services.dify_interview_service.httpx.AsyncClient",
        FakeAsyncClient,
    )
    service = DifyInterviewService()
    upload_id = await service._upload_image(
        path=image_path,
        name="screen.png",
        mime_type="image/png",
        user="interview:session-1",
    )

    assert upload_id == "dify-upload-id"
    assert captured["url"].endswith("/files/upload")
    assert captured["data"] == {"user": "interview:session-1"}
    assert captured["files"]["file"][0:3:2] == ("screen.png", "image/png")
