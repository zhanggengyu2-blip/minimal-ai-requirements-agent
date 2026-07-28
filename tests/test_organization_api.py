from fastapi.testclient import TestClient

from app.main import app


def test_department_and_invitation_management():
    with TestClient(app) as client:
        create_department = client.post(
            "/api/v1/departments",
            json={"name": "客户成功部"},
        )
        assert create_department.status_code == 201
        department = create_department.json()["data"]
        assert department["status"] == "ACTIVE"

        update_department = client.patch(
            f"/api/v1/departments/{department['id']}",
            json={"name": "客户体验部"},
        )
        assert update_department.status_code == 200
        assert update_department.json()["data"]["name"] == "客户体验部"

        invitation_response = client.post(
            "/api/v1/invitations",
            json={"department_id": department["id"], "user_name": "测试用户"},
        )
        assert invitation_response.status_code == 201
        invitation = invitation_response.json()["data"]
        assert invitation["status"] == "UNUSED"
        assert invitation["department_name"] == "客户体验部"
        assert len(invitation["code"]) == 9

        list_response = client.get(
            "/api/v1/invitations",
            params={"department_id": department["id"], "status": "UNUSED"},
        )
        assert list_response.status_code == 200
        assert list_response.json()["data"]["total"] == 1

        disable_response = client.post(
            f"/api/v1/invitations/{invitation['id']}/disable",
        )
        assert disable_response.status_code == 200
        assert disable_response.json()["data"]["status"] == "DISABLED"
