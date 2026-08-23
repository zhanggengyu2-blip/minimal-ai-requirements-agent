from contextlib import contextmanager
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_auth_context
from app.core.security import normalize_name
from app.db.models import Task, TaskLane, UserAccount, UserRole
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
        json={"name": name, "project_context": f"{name}上下文"},
    )
    assert response.status_code == 201
    return response.json()["data"]


def _add_member(client: TestClient, project: dict, admin: UserAccount, member: UserAccount):
    response = client.put(
        f"/api/v1/projects/{project['id']}/members",
        json={
            "user_ids": [admin.id, member.id],
            "expected_member_revision": project["member_revision"],
        },
    )
    assert response.status_code == 200


def _create_task(
    client: TestClient,
    project_id: str,
    assignee_id: str,
    name: str,
    **overrides,
) -> dict:
    payload = {"name": name, "assignee_id": assignee_id, **overrides}
    response = client.post(f"/api/v1/projects/{project_id}/tasks", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_task_create_list_defaults_filters_and_truncation(db_session):
    admin = _admin(db_session)
    member = _member(db_session, "任务筛选成员")
    with TestClient(app) as client:
        project = _create_project(client, "任务查询项目")
        _add_member(client, project, admin, member)
        first = _create_task(client, project["id"], admin.id, "导出 100%_完整数据")
        second = _create_task(
            client,
            project["id"],
            admin.id,
            "导出 100XX完整数据",
            status="IN_PROGRESS",
            priority="P0",
        )
        third = _create_task(
            client,
            project["id"],
            member.id,
            "已完成任务",
            status="COMPLETED",
        )

        all_tasks = client.get(
            f"/api/v1/projects/{project['id']}/tasks", params={"limit": 2}
        )
        literal_search = client.get(
            f"/api/v1/projects/{project['id']}/tasks",
            params={"keyword": "100%_", "status": "ALL"},
        )
        unfinished = client.get(
            f"/api/v1/projects/{project['id']}/tasks",
            params={"status": "UNFINISHED"},
        )
        detail = client.get(f"/api/v1/projects/{project['id']}/tasks/{first['id']}")

    assert first["status"] == "NOT_STARTED"
    assert first["priority"] == "P1"
    assert first["sort_order"] == 1
    assert second["sort_order"] == 2
    assert third["sort_order"] == 1
    assert all_tasks.status_code == 200
    assert all_tasks.json()["data"]["total"] == 3
    assert all_tasks.json()["data"]["limit"] == 2
    assert all_tasks.json()["data"]["truncated"] is True
    assert len(all_tasks.json()["data"]["items"]) == 2
    assert {lane["assignee_id"] for lane in all_tasks.json()["data"]["lanes"]} == {
        admin.id,
        member.id,
    }
    assert [item["id"] for item in literal_search.json()["data"]["items"]] == [first["id"]]
    assert {item["id"] for item in unfinished.json()["data"]["items"]} == {
        first["id"],
        second["id"],
    }
    assert detail.status_code == 200


def test_task_creation_validates_assignee_dates_description_and_version(db_session):
    admin = _admin(db_session)
    outsider = _member(db_session, "非项目成员")
    with TestClient(app) as client:
        project = _create_project(client, "任务校验项目")
        invalid_assignee = client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={"name": "无效负责人", "assignee_id": outsider.id},
        )
        invalid_dates = client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={
                "name": "日期错误",
                "assignee_id": admin.id,
                "start_date": "2026-09-02",
                "due_date": "2026-09-01",
            },
        )
        oversized = client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={"name": "描述过长", "assignee_id": admin.id, "description": "x" * 501},
        )
        missing_version = client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={
                "name": "不存在版本",
                "assignee_id": admin.id,
                "version_id": "v" * 32,
            },
        )
        excessive_limit = client.get(
            f"/api/v1/projects/{project['id']}/tasks", params={"limit": 1001}
        )

    assert invalid_assignee.status_code == 409
    assert invalid_assignee.json()["code"] == "TASK_ASSIGNEE_NOT_PROJECT_MEMBER"
    assert invalid_dates.status_code == 422
    assert oversized.status_code == 422
    assert missing_version.status_code == 404
    assert excessive_limit.status_code == 422


def test_task_update_moves_to_lane_bottom_and_rejects_stale_or_invalid_dates(db_session):
    admin = _admin(db_session)
    member = _member(db_session, "任务转交成员")
    with TestClient(app) as client:
        project = _create_project(client, "任务转交项目")
        _add_member(client, project, admin, member)
        member_task = _create_task(client, project["id"], member.id, "成员原有任务")
        moving = _create_task(
            client,
            project["id"],
            admin.id,
            "待转交任务",
            start_date="2026-09-05",
        )
        moved = client.patch(
            f"/api/v1/projects/{project['id']}/tasks/{moving['id']}",
            json={"expected_revision": 1, "assignee_id": member.id},
        )
        stale = client.patch(
            f"/api/v1/projects/{project['id']}/tasks/{moving['id']}",
            json={"expected_revision": 1, "name": "过期覆盖"},
        )
        invalid_due = client.patch(
            f"/api/v1/projects/{project['id']}/tasks/{moving['id']}",
            json={"expected_revision": 2, "due_date": "2026-09-04"},
        )
        null_name = client.patch(
            f"/api/v1/projects/{project['id']}/tasks/{moving['id']}",
            json={"expected_revision": 2, "name": None},
        )
        order = client.get(
            f"/api/v1/projects/{project['id']}/task-lanes/{member.id}/order"
        )

    assert moved.status_code == 200
    assert moved.json()["data"]["assignee_id"] == member.id
    assert moved.json()["data"]["sort_order"] == 2
    assert moved.json()["data"]["revision"] == 2
    assert stale.status_code == 409
    assert stale.json()["code"] == "TASK_REVISION_CONFLICT"
    assert invalid_due.status_code == 422
    assert invalid_due.json()["code"] == "TASK_DATE_INVALID"
    assert null_name.status_code == 422
    assert order.json()["data"]["ordered_task_ids"] == [member_task["id"], moving["id"]]
    assert order.json()["data"]["lane_revision"] == 3


def test_complete_lane_reorder_preserves_filtered_relative_order(db_session):
    admin = _admin(db_session)
    with TestClient(app) as client:
        project = _create_project(client, "泳道排序项目")
        first = _create_task(client, project["id"], admin.id, "任务一")
        second = _create_task(
            client, project["id"], admin.id, "任务二", status="COMPLETED"
        )
        third = _create_task(client, project["id"], admin.id, "任务三")
        before = client.get(
            f"/api/v1/projects/{project['id']}/task-lanes/{admin.id}/order"
        ).json()["data"]
        reversed_ids = [third["id"], second["id"], first["id"]]
        reordered = client.put(
            f"/api/v1/projects/{project['id']}/task-lanes/{admin.id}/order",
            json={
                "expected_lane_revision": before["lane_revision"],
                "ordered_task_ids": reversed_ids,
            },
        )
        filtered = client.get(
            f"/api/v1/projects/{project['id']}/tasks",
            params={"status": "UNFINISHED"},
        )
        incomplete = client.put(
            f"/api/v1/projects/{project['id']}/task-lanes/{admin.id}/order",
            json={
                "expected_lane_revision": reordered.json()["data"]["lane_revision"],
                "ordered_task_ids": [first["id"], third["id"]],
            },
        )
        stale = client.put(
            f"/api/v1/projects/{project['id']}/task-lanes/{admin.id}/order",
            json={
                "expected_lane_revision": before["lane_revision"],
                "ordered_task_ids": reversed_ids,
            },
        )

    assert before["lane_revision"] == 4
    assert reordered.status_code == 200
    assert reordered.json()["data"]["ordered_task_ids"] == reversed_ids
    assert reordered.json()["data"]["lane_revision"] == 5
    assert [item["id"] for item in filtered.json()["data"]["items"]] == [
        third["id"],
        first["id"],
    ]
    assert incomplete.status_code == 409
    assert incomplete.json()["code"] == "TASK_LANE_ORDER_INVALID"
    assert stale.status_code == 409
    assert stale.json()["code"] == "LANE_REVISION_CONFLICT"


def test_task_delete_is_permanent_and_revision_protected(db_session):
    admin = _admin(db_session)
    with TestClient(app) as client:
        project = _create_project(client, "任务删除项目")
        task = _create_task(client, project["id"], admin.id, "待删除任务")
        updated = client.patch(
            f"/api/v1/projects/{project['id']}/tasks/{task['id']}",
            json={"expected_revision": 1, "description": "已更新"},
        ).json()["data"]
        stale = client.delete(
            f"/api/v1/projects/{project['id']}/tasks/{task['id']}",
            params={"expected_revision": 1},
        )
        deleted = client.delete(
            f"/api/v1/projects/{project['id']}/tasks/{task['id']}",
            params={"expected_revision": updated["revision"]},
        )
        missing = client.get(f"/api/v1/projects/{project['id']}/tasks/{task['id']}")
        order = client.get(
            f"/api/v1/projects/{project['id']}/task-lanes/{admin.id}/order"
        )

    assert stale.status_code == 409
    assert deleted.status_code == 200
    assert missing.status_code == 404
    assert order.json()["data"]["ordered_task_ids"] == []
    assert order.json()["data"]["lane_revision"] == 3
    assert db_session.get(Task, task["id"]) is None


def test_archived_project_allows_reads_but_rejects_all_task_writes(db_session):
    admin = _admin(db_session)
    with TestClient(app) as client:
        project = _create_project(client, "归档任务项目")
        task = _create_task(client, project["id"], admin.id, "归档前任务")
        order = client.get(
            f"/api/v1/projects/{project['id']}/task-lanes/{admin.id}/order"
        ).json()["data"]
        archived = client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"expected_revision": 1, "status": "ARCHIVED"},
        )
        readable = client.get(f"/api/v1/projects/{project['id']}/tasks")
        create = client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={"name": "归档后新增", "assignee_id": admin.id},
        )
        update = client.patch(
            f"/api/v1/projects/{project['id']}/tasks/{task['id']}",
            json={"expected_revision": 1, "name": "归档后修改"},
        )
        delete = client.delete(
            f"/api/v1/projects/{project['id']}/tasks/{task['id']}",
            params={"expected_revision": 1},
        )
        reorder = client.put(
            f"/api/v1/projects/{project['id']}/task-lanes/{admin.id}/order",
            json={
                "expected_lane_revision": order["lane_revision"],
                "ordered_task_ids": [task["id"]],
            },
        )

    assert archived.status_code == 200
    assert readable.status_code == 200
    assert readable.json()["data"]["total"] == 1
    for response in (create, update, delete, reorder):
        assert response.status_code == 403
        assert response.json()["code"] == "PERMISSION_DENIED"


def test_nonmember_cannot_discover_tasks_and_admin_must_join_before_writes(db_session):
    admin = _admin(db_session)
    member = _member(db_session, "任务项目创建者")
    with authenticated_as(member) as member_client:
        project = _create_project(member_client, "管理员只读任务项目")
        task = _create_task(member_client, project["id"], member.id, "成员创建任务")

    outsider = _member(db_session, "任务越权成员")
    with authenticated_as(outsider) as outsider_client:
        hidden_list = outsider_client.get(f"/api/v1/projects/{project['id']}/tasks")
        hidden_detail = outsider_client.get(
            f"/api/v1/projects/{project['id']}/tasks/{task['id']}"
        )

    with TestClient(app) as admin_client:
        admin_read = admin_client.get(f"/api/v1/projects/{project['id']}/tasks")
        admin_write = admin_client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={"name": "管理员未加入写入", "assignee_id": member.id},
        )

    assert hidden_list.status_code == 404
    assert hidden_detail.status_code == 404
    assert admin_read.status_code == 200
    assert admin_write.status_code == 403
    assert db_session.get(TaskLane, (project["id"], member.id)) is not None
