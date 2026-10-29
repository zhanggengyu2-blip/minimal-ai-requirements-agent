from contextlib import contextmanager
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_auth_context
from app.core.security import normalize_name
from app.db.models import Task, UserAccount, UserRole, VersionParticipant
from app.main import app


def _admin(db_session) -> UserAccount:
    admin = db_session.scalar(select(UserAccount).where(UserAccount.role == UserRole.ADMIN))
    assert admin is not None
    return admin


def _member(db_session, name: str) -> UserAccount:
    admin = _admin(db_session)
    member = UserAccount(
        department_id=admin.department_id,
        name=name,
        normalized_name=normalize_name(name),
        role=UserRole.MEMBER,
    )
    db_session.add(member)
    db_session.commit()
    return member


@contextmanager
def authenticated_as(user: UserAccount):
    previous = app.dependency_overrides.get(get_auth_context)
    app.dependency_overrides[get_auth_context] = lambda: SimpleNamespace(
        user=user,
        csrf_token="test-csrf",
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
        json={"name": name, "project_context": f"{name}上下文"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _add_member(
    client: TestClient,
    project: dict,
    admin: UserAccount,
    member: UserAccount,
) -> dict:
    response = client.put(
        f"/api/v1/projects/{project['id']}/members",
        json={
            "user_ids": [admin.id, member.id],
            "expected_member_revision": project["member_revision"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_version(
    client: TestClient,
    project_id: str,
    name: str,
    participant_ids: list[str],
    **overrides,
) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/versions",
        json={
            "name": name,
            "start_date": "2026-08-24",
            "end_date": "2026-09-11",
            "participant_ids": participant_ids,
            **overrides,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _create_task(
    client: TestClient,
    project_id: str,
    assignee_id: str,
    name: str,
    **overrides,
) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"name": name, "assignee_id": assignee_id, **overrides},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_version_create_list_detail_and_validation(db_session):
    admin = _admin(db_session)
    member = _member(db_session, "版本参与成员")
    outsider = _member(db_session, "版本外部成员")
    with TestClient(app) as client:
        project = _create_project(client, "版本基础项目")
        _add_member(client, project, admin, member)
        first = _create_version(
            client,
            project["id"],
            "V1.0",
            [member.id, admin.id],
        )
        second = _create_version(client, project["id"], "V2.0", [admin.id])
        versions = client.get(f"/api/v1/projects/{project['id']}/versions")
        detail = client.get(
            f"/api/v1/projects/{project['id']}/versions/{first['id']}"
        )
        duplicate = client.post(
            f"/api/v1/projects/{project['id']}/versions",
            json={
                "name": "V1.0",
                "start_date": "2026-09-01",
                "end_date": "2026-09-10",
                "participant_ids": [admin.id],
            },
        )
        invalid_participant = client.post(
            f"/api/v1/projects/{project['id']}/versions",
            json={
                "name": "V3.0",
                "start_date": "2026-09-01",
                "end_date": "2026-09-10",
                "participant_ids": [outsider.id],
            },
        )
        invalid_dates = client.post(
            f"/api/v1/projects/{project['id']}/versions",
            json={
                "name": "日期错误",
                "start_date": "2026-09-11",
                "end_date": "2026-09-10",
                "participant_ids": [admin.id],
            },
        )
        no_participant = client.post(
            f"/api/v1/projects/{project['id']}/versions",
            json={
                "name": "无人版本",
                "start_date": "2026-09-01",
                "end_date": "2026-09-10",
                "participant_ids": [],
            },
        )

    assert first["status"] == "NOT_STARTED"
    assert first["revision"] == 1
    assert [item["user_id"] for item in detail.json()["data"]["participants"]] == [
        admin.id,
        member.id,
    ]
    assert versions.status_code == 200
    assert versions.json()["data"]["total"] == 2
    assert versions.json()["data"]["items"][0]["id"] == second["id"]
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "VERSION_NAME_ALREADY_EXISTS"
    assert invalid_participant.status_code == 409
    assert invalid_participant.json()["code"] == "VERSION_PARTICIPANT_NOT_PROJECT_MEMBER"
    assert invalid_dates.status_code == 422
    assert no_participant.status_code == 422


def test_version_update_impact_revision_and_participant_removal(db_session):
    admin = _admin(db_session)
    member = _member(db_session, "版本任务成员")
    with TestClient(app) as client:
        project = _create_project(client, "版本修改项目")
        _add_member(client, project, admin, member)
        version = _create_version(
            client,
            project["id"],
            "V1.0",
            [admin.id, member.id],
        )
        unfinished = _create_task(
            client,
            project["id"],
            member.id,
            "未完成版本任务",
            version_id=version["id"],
            status="IN_PROGRESS",
        )
        completed = _create_task(
            client,
            project["id"],
            admin.id,
            "已完成版本任务",
            version_id=version["id"],
            status="COMPLETED",
        )
        blocked = client.patch(
            f"/api/v1/projects/{project['id']}/versions/{version['id']}",
            json={"expected_revision": 1, "participant_ids": [admin.id]},
        )
        updated = client.patch(
            f"/api/v1/projects/{project['id']}/versions/{version['id']}",
            json={
                "expected_revision": 1,
                "name": "V1.0 已完成",
                "status": "COMPLETED",
                "participant_ids": [admin.id, member.id],
            },
        )
        stale = client.patch(
            f"/api/v1/projects/{project['id']}/versions/{version['id']}",
            json={"expected_revision": 1, "status": "IN_PROGRESS"},
        )
        impact = client.get(
            f"/api/v1/projects/{project['id']}/versions/{version['id']}/completion-impact"
        )
        tasks = client.get(
            f"/api/v1/projects/{project['id']}/tasks",
            params={"version_id": version["id"], "status": "ALL"},
        )

    assert blocked.status_code == 409
    assert blocked.json()["code"] == "VERSION_PARTICIPANT_HAS_TASKS"
    assert updated.status_code == 200
    assert updated.json()["data"]["revision"] == 2
    assert updated.json()["data"]["status"] == "COMPLETED"
    assert stale.status_code == 409
    assert stale.json()["code"] == "VERSION_REVISION_CONFLICT"
    assert impact.json()["data"] == {
        "version_id": version["id"],
        "task_count": 2,
        "unfinished_task_count": 1,
    }
    task_statuses = {item["id"]: item["status"] for item in tasks.json()["data"]["items"]}
    assert task_statuses == {
        unfinished["id"]: "IN_PROGRESS",
        completed["id"]: "COMPLETED",
    }


def test_task_assignment_automatically_adds_version_participant(db_session):
    admin = _admin(db_session)
    member = _member(db_session, "自动加入版本成员")
    moved_member = _member(db_session, "修改后加入版本成员")
    with TestClient(app) as client:
        project = _create_project(client, "版本自动成员项目")
        members = _add_member(client, project, admin, member)
        expanded_members = client.put(
            f"/api/v1/projects/{project['id']}/members",
            json={
                "user_ids": [admin.id, member.id, moved_member.id],
                "expected_member_revision": members["member_revision"],
            },
        )
        assert expanded_members.status_code == 200
        version = _create_version(client, project["id"], "V1.0", [admin.id])
        task = _create_task(
            client,
            project["id"],
            member.id,
            "自动加入参与人员的任务",
            version_id=version["id"],
        )
        moved_task = _create_task(
            client,
            project["id"],
            moved_member.id,
            "编辑后加入版本的任务",
        )
        moved = client.patch(
            f"/api/v1/projects/{project['id']}/tasks/{moved_task['id']}",
            json={"expected_revision": 1, "version_id": version["id"]},
        )
        assert moved.status_code == 200
        detail = client.get(
            f"/api/v1/projects/{project['id']}/versions/{version['id']}"
        )

    participants = detail.json()["data"]["participants"]
    assert [item["user_id"] for item in participants] == [
        admin.id,
        member.id,
        moved_member.id,
    ]
    assert [item["task_count"] for item in participants] == [0, 1, 1]
    assert detail.json()["data"]["revision"] == 3
    assert db_session.get(VersionParticipant, (version["id"], member.id)) is not None
    assert task["version_id"] == version["id"]
    assert moved.json()["data"]["version_id"] == version["id"]


def test_version_delete_unlinks_tasks_and_returns_latest_remaining_version(db_session):
    admin = _admin(db_session)
    with TestClient(app) as client:
        project = _create_project(client, "版本删除项目")
        first = _create_version(client, project["id"], "V1.0", [admin.id])
        second = _create_version(client, project["id"], "V2.0", [admin.id])
        task = _create_task(
            client,
            project["id"],
            admin.id,
            "删除版本后保留的任务",
            version_id=first["id"],
        )
        updated = client.patch(
            f"/api/v1/projects/{project['id']}/versions/{first['id']}",
            json={"expected_revision": 1, "status": "IN_PROGRESS"},
        ).json()["data"]
        stale = client.delete(
            f"/api/v1/projects/{project['id']}/versions/{first['id']}",
            params={"expected_revision": 1},
        )
        deleted = client.delete(
            f"/api/v1/projects/{project['id']}/versions/{first['id']}",
            params={"expected_revision": updated["revision"]},
        )
        retained_task = client.get(
            f"/api/v1/projects/{project['id']}/tasks/{task['id']}"
        )
        missing_version = client.get(
            f"/api/v1/projects/{project['id']}/versions/{first['id']}"
        )

    assert stale.status_code == 409
    assert stale.json()["code"] == "VERSION_REVISION_CONFLICT"
    assert deleted.status_code == 200
    assert deleted.json()["data"] == {
        "unlinked_task_count": 1,
        "next_version_id": second["id"],
    }
    assert retained_task.json()["data"]["version_id"] is None
    assert retained_task.json()["data"]["revision"] == 2
    assert missing_version.status_code == 404
    assert db_session.get(Task, task["id"]) is not None


def test_version_permissions_archived_reads_and_project_member_cleanup(db_session):
    admin = _admin(db_session)
    member = _member(db_session, "版本项目创建者")
    zero_task_member = _member(db_session, "零任务版本参与者")
    outsider = _member(db_session, "版本不可见成员")
    with authenticated_as(member) as member_client:
        project = _create_project(member_client, "版本权限项目")
        members = member_client.put(
            f"/api/v1/projects/{project['id']}/members",
            json={
                "user_ids": [member.id, zero_task_member.id],
                "expected_member_revision": project["member_revision"],
            },
        ).json()["data"]
        version = _create_version(
            member_client,
            project["id"],
            "V1.0",
            [member.id, zero_task_member.id],
        )
        sole_participant_version = _create_version(
            member_client,
            project["id"],
            "仅一名参与者",
            [zero_task_member.id],
        )
        blocked_last_participant = member_client.put(
            f"/api/v1/projects/{project['id']}/members",
            json={
                "user_ids": [member.id],
                "expected_member_revision": members["member_revision"],
            },
        )
        expanded = member_client.patch(
            f"/api/v1/projects/{project['id']}/versions/{sole_participant_version['id']}",
            json={
                "expected_revision": sole_participant_version["revision"],
                "participant_ids": [member.id, zero_task_member.id],
            },
        )
        assert expanded.status_code == 200
        removed = member_client.put(
            f"/api/v1/projects/{project['id']}/members",
            json={
                "user_ids": [member.id],
                "expected_member_revision": members["member_revision"],
            },
        )
        after_removal = member_client.get(
            f"/api/v1/projects/{project['id']}/versions/{version['id']}"
        )
        archived = member_client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"expected_revision": 1, "status": "ARCHIVED"},
        )
        archived_list = member_client.get(
            f"/api/v1/projects/{project['id']}/versions"
        )
        archived_write = member_client.patch(
            f"/api/v1/projects/{project['id']}/versions/{version['id']}",
            json={
                "expected_revision": after_removal.json()["data"]["revision"],
                "status": "COMPLETED",
            },
        )

    with authenticated_as(outsider) as outsider_client:
        hidden = outsider_client.get(f"/api/v1/projects/{project['id']}/versions")

    with TestClient(app) as admin_client:
        admin_visible = admin_client.get(f"/api/v1/projects/{project['id']}/versions")
        admin_write = admin_client.post(
            f"/api/v1/projects/{project['id']}/versions",
            json={
                "name": "管理员未加入写入",
                "start_date": "2026-09-01",
                "end_date": "2026-09-10",
                "participant_ids": [member.id],
            },
        )

    assert blocked_last_participant.status_code == 409
    assert blocked_last_participant.json()["code"] == "PROJECT_MEMBER_LAST_VERSION_PARTICIPANT"
    assert removed.status_code == 200
    assert [
        item["user_id"] for item in after_removal.json()["data"]["participants"]
    ] == [member.id]
    assert after_removal.json()["data"]["revision"] == 2
    assert archived.status_code == 200
    assert archived_list.status_code == 200
    assert archived_write.status_code == 403
    assert archived_write.json()["code"] == "PROJECT_ARCHIVED"
    assert hidden.status_code == 404
    assert admin_visible.status_code == 200
    assert admin_write.status_code == 403
    assert admin_write.json()["code"] == "PERMISSION_DENIED"
