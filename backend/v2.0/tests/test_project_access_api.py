from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_auth_context
from app.core.security import normalize_name
from app.db.models import (
    InterviewSession,
    ProjectMember,
    Requirement,
    Task,
    UserAccount,
    UserRole,
)
from app.main import app


def _admin(db_session) -> UserAccount:
    admin = db_session.scalar(select(UserAccount).where(UserAccount.role == UserRole.ADMIN))
    assert admin is not None
    return admin


def _member(db_session, name: str) -> UserAccount:
    admin = _admin(db_session)
    user = UserAccount(
        department_id=admin.department_id,
        name=name,
        normalized_name=normalize_name(name),
        role=UserRole.MEMBER,
    )
    db_session.add(user)
    db_session.commit()
    return user


@contextmanager
def authenticated_as(user: UserAccount):
    previous = app.dependency_overrides.get(get_auth_context)
    app.dependency_overrides[get_auth_context] = lambda: SimpleNamespace(
        user=user, csrf_token="test-csrf"
    )
    try:
        with TestClient(app) as client:
            yield client
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_auth_context, None)
        else:
            app.dependency_overrides[get_auth_context] = previous


def _create_project(client: TestClient, name: str) -> dict:
    response = client.post(
        "/api/v1/projects",
        json={"name": name, "project_context": f"{name}的项目背景"},
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_project_creator_is_first_member(db_session):
    admin = _admin(db_session)
    with TestClient(app) as client:
        project = _create_project(client, "首位成员项目")
        members = client.get(f"/api/v1/projects/{project['id']}/members")

    assert project["revision"] == 1
    assert project["member_revision"] == 1
    assert project["member_count"] == 1
    assert members.status_code == 200
    assert members.json()["data"]["member_revision"] == 1
    assert [item["user_id"] for item in members.json()["data"]["items"]] == [admin.id]
    assert db_session.get(ProjectMember, (project["id"], admin.id)) is not None


def test_member_visibility_covers_projects_requirements_and_interviews(db_session):
    admin = _admin(db_session)
    member = _member(db_session, "可见性成员")
    with TestClient(app) as admin_client:
        visible = _create_project(admin_client, "成员可见项目")
        hidden = _create_project(admin_client, "成员不可见项目")
        saved = admin_client.put(
            f"/api/v1/projects/{visible['id']}/members",
            json={
                "user_ids": [admin.id, member.id],
                "expected_member_revision": visible["member_revision"],
            },
        )
        assert saved.status_code == 200

    visible_requirement = Requirement(project_id=visible["id"], raw_content="可见需求")
    hidden_requirement = Requirement(project_id=hidden["id"], raw_content="不可见需求")
    hidden_interview = InterviewSession(
        project_id=hidden["id"], created_by=admin.id, raw_content="不可见访谈"
    )
    db_session.add_all([visible_requirement, hidden_requirement, hidden_interview])
    db_session.commit()

    with authenticated_as(member) as member_client:
        project_list = member_client.get("/api/v1/projects")
        hidden_project = member_client.get(f"/api/v1/projects/{hidden['id']}")
        hidden_members = member_client.get(f"/api/v1/projects/{hidden['id']}/members")
        requirement_list = member_client.get("/api/v1/requirements")
        hidden_requirement_response = member_client.get(
            f"/api/v1/requirements/{hidden_requirement.id}"
        )
        hidden_interview_response = member_client.get(
            f"/api/v1/interviews/{hidden_interview.id}"
        )

    assert project_list.status_code == 200
    assert [item["id"] for item in project_list.json()["data"]["items"]] == [visible["id"]]
    assert hidden_project.status_code == 404
    assert hidden_members.status_code == 404
    assert requirement_list.status_code == 200
    assert [item["id"] for item in requirement_list.json()["data"]["items"]] == [
        visible_requirement.id
    ]
    assert hidden_requirement_response.status_code == 404
    assert hidden_interview_response.status_code == 404

    with authenticated_as(member) as member_client:
        current_members = member_client.get(
            f"/api/v1/projects/{visible['id']}/members"
        ).json()["data"]
        member_saved = member_client.put(
            f"/api/v1/projects/{visible['id']}/members",
            json={
                "user_ids": [member.id],
                "expected_member_revision": current_members["member_revision"],
            },
        )
    assert member_saved.status_code == 200
    assert [item["user_id"] for item in member_saved.json()["data"]["items"]] == [
        member.id
    ]

    with TestClient(app) as admin_client:
        admin_projects = admin_client.get("/api/v1/projects")
        admin_hidden = admin_client.get(f"/api/v1/projects/{hidden['id']}")
    assert admin_projects.json()["data"]["total"] == 2
    assert admin_hidden.status_code == 200


def test_admin_can_maintain_members_but_must_join_before_project_writes(db_session):
    admin = _admin(db_session)
    member = _member(db_session, "项目创建成员")
    with authenticated_as(member) as member_client:
        project = _create_project(member_client, "成员创建项目")

    with TestClient(app) as admin_client:
        forbidden = admin_client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"expected_revision": 1, "description": "管理员尚未加入"},
        )
        members = admin_client.get(f"/api/v1/projects/{project['id']}/members")
        joined = admin_client.put(
            f"/api/v1/projects/{project['id']}/members",
            json={
                "user_ids": [member.id, admin.id],
                "expected_member_revision": members.json()["data"]["member_revision"],
            },
        )
        updated = admin_client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"expected_revision": 1, "description": "管理员已经加入"},
        )

    assert forbidden.status_code == 403
    assert members.status_code == 200
    assert joined.status_code == 200
    assert {item["user_id"] for item in joined.json()["data"]["items"]} == {
        member.id,
        admin.id,
    }
    assert updated.status_code == 200
    assert updated.json()["data"]["revision"] == 2


def test_member_collection_requires_nonempty_fresh_complete_set(db_session):
    admin = _admin(db_session)
    member = _member(db_session, "成员修订测试")
    with TestClient(app) as client:
        project = _create_project(client, "成员修订项目")
        empty = client.put(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_ids": [], "expected_member_revision": 1},
        )
        first = client.put(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_ids": [admin.id, member.id], "expected_member_revision": 1},
        )
        stale = client.put(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_ids": [admin.id], "expected_member_revision": 1},
        )

    assert empty.status_code == 422
    assert first.status_code == 200
    assert first.json()["data"]["member_revision"] == 2
    assert stale.status_code == 409
    assert stale.json()["code"] == "PROJECT_MEMBER_REVISION_CONFLICT"
    assert stale.json()["details"]["current_member_revision"] == 2


def test_archive_is_readonly_and_member_can_reopen(db_session):
    admin = _admin(db_session)
    with TestClient(app) as client:
        project = _create_project(client, "归档只读项目")
        archived = client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"expected_revision": 1, "status": "ARCHIVED"},
        )
        assert archived.status_code == 200

        with patch(
            "app.services.dify_service.DifyService.analyze_requirement",
            new=AsyncMock(),
        ) as analyze:
            requirement = client.post(
                "/api/v1/requirements",
                json={"project_id": project["id"], "raw_content": "不应写入的需求"},
            )
        member_write = client.put(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_ids": [admin.id], "expected_member_revision": 1},
        )
        edit = client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"expected_revision": 2, "name": "归档后改名"},
        )
        reopened = client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"expected_revision": 2, "status": "ACTIVE"},
        )
        stale = client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"expected_revision": 2, "description": "过期修改"},
        )

    assert requirement.status_code == 403
    assert requirement.json()["code"] == "PROJECT_ARCHIVED"
    analyze.assert_not_awaited()
    assert member_write.status_code == 403
    assert member_write.json()["code"] == "PROJECT_ARCHIVED"
    assert edit.status_code == 403
    assert edit.json()["code"] == "PROJECT_ARCHIVED"
    assert reopened.status_code == 200
    assert reopened.json()["data"]["revision"] == 3
    assert stale.status_code == 409
    assert stale.json()["code"] == "PROJECT_REVISION_CONFLICT"


def test_member_with_assigned_task_cannot_be_removed(db_session):
    admin = _admin(db_session)
    member = _member(db_session, "任务负责人")
    with TestClient(app) as client:
        project = _create_project(client, "成员任务约束项目")
        added = client.put(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_ids": [admin.id, member.id], "expected_member_revision": 1},
        )
        assert added.status_code == 200

        db_session.add(
            Task(
                id="t" * 32,
                project_id=project["id"],
                assignee_id=member.id,
                name="成员仍负责的任务",
                sort_order=1,
                created_by=admin.id,
                updated_by=admin.id,
            )
        )
        db_session.commit()

        blocked = client.put(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_ids": [admin.id], "expected_member_revision": 2},
        )

    assert blocked.status_code == 409
    assert blocked.json()["code"] == "PROJECT_MEMBER_HAS_TASKS"
    assert blocked.json()["details"]["task_counts"] == {member.id: 1}
    remaining = set(
        db_session.scalars(
            select(ProjectMember.user_id).where(ProjectMember.project_id == project["id"])
        )
    )
    assert remaining == {admin.id, member.id}
