from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.deps import get_auth_context
from app.core.config import get_settings
from app.db.models import AuthSession, Department, InvitationCode, UserAccount, UserRole, utc_now
from app.main import app
from app.core.exceptions import ConflictError
from app.services.auth_service import AuthService


@contextmanager
def real_authentication():
    saved_override = app.dependency_overrides.pop(get_auth_context, None)
    settings = get_settings()
    previous_csrf = settings.csrf_enabled
    settings.csrf_enabled = True
    try:
        yield
    finally:
        settings.csrf_enabled = previous_csrf
        if saved_override is not None:
            app.dependency_overrides[get_auth_context] = saved_override


def _admin_identity(db_session) -> tuple[str, str]:
    admin = db_session.scalar(select(UserAccount).where(UserAccount.role == UserRole.ADMIN))
    assert admin is not None
    return admin.department_id, admin.name


def _login_admin(client: TestClient, db_session) -> str:
    department_id, name = _admin_identity(db_session)
    response = client.post(
        "/api/v1/auth/sessions",
        json={
            "department_id": department_id,
            "name": name,
            "shared_password": "test-shared-password",
        },
    )
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    return response.json()["data"]["csrf_token"]


def test_public_departments_and_protected_routes(db_session):
    with real_authentication(), TestClient(app) as client:
        public = client.get("/api/v1/auth/departments")
        protected = client.get("/api/v1/projects")
        invalid = client.post(
            "/api/v1/auth/sessions",
            json={
                "department_id": "0" * 32,
                "name": "不存在",
                "shared_password": "wrong-password",
            },
        )

    assert public.status_code == 200
    assert len(public.json()["data"]) == 3
    assert protected.status_code == 401
    assert protected.json()["code"] == "AUTH_SESSION_EXPIRED"
    assert invalid.status_code == 401
    assert invalid.json()["code"] == "AUTH_IDENTITY_MISMATCH"
    assert "wrong-password" not in invalid.text


def test_login_csrf_me_and_logout(db_session):
    with real_authentication(), TestClient(app) as client:
        csrf = _login_admin(client, db_session)
        me = client.get("/api/v1/auth/me")
        missing_csrf = client.post("/api/v1/departments", json={"name": "CSRF失败部门"})
        created = client.post(
            "/api/v1/departments",
            json={"name": "CSRF成功部门"},
            headers={"X-CSRF-Token": csrf},
        )
        logout = client.delete(
            "/api/v1/auth/session", headers={"X-CSRF-Token": csrf}
        )
        after_logout = client.get("/api/v1/auth/me")

    assert me.status_code == 200
    assert me.json()["data"]["user"]["role"] == "ADMIN"
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["code"] == "PERMISSION_DENIED"
    assert created.status_code == 201
    assert logout.status_code == 200
    assert after_logout.status_code == 401


def test_invitation_registration_storage_and_member_permissions(db_session):
    with real_authentication(), TestClient(app) as admin_client:
        csrf = _login_admin(admin_client, db_session)
        department = db_session.scalar(select(Department).where(Department.name == "运营部"))
        invitation_response = admin_client.post(
            "/api/v1/invitations",
            json={
                "department_id": department.id,
                "intended_user_name": "陈晨",
            },
            headers={"X-CSRF-Token": csrf},
        )
        assert invitation_response.status_code == 201
        invitation_data = invitation_response.json()["data"]
        code = invitation_data["code"]

        db_session.expire_all()
        stored = db_session.get(InvitationCode, invitation_data["id"])
        assert stored is not None
        assert code not in stored.code_ciphertext
        assert code not in stored.code_digest

        with TestClient(app) as member_client:
            registration = member_client.post(
                "/api/v1/auth/registrations",
                json={
                    "department_id": department.id,
                    "name": "陈晨",
                    "invitation_code": code,
                },
            )
            assert registration.status_code == 201
            member_csrf = registration.json()["data"]["csrf_token"]
            assert registration.json()["data"]["user"]["role"] == "MEMBER"

            users = member_client.get("/api/v1/users")
            forbidden = member_client.post(
                "/api/v1/departments",
                json={"name": "普通成员无权创建"},
                headers={"X-CSRF-Token": member_csrf},
            )

        reused = admin_client.post(
            "/api/v1/auth/registrations",
            json={
                "department_id": department.id,
                "name": "陈晨",
                "invitation_code": code,
            },
        )

        with TestClient(app) as login_client:
            login = login_client.post(
                "/api/v1/auth/sessions",
                json={
                    "department_id": department.id,
                    "name": "陈晨",
                    "shared_password": "test-shared-password",
                },
            )

    assert users.status_code == 200
    assert forbidden.status_code == 403
    assert reused.status_code == 409
    assert reused.json()["code"] == "AUTH_INVITATION_USED"
    assert login.status_code == 200


def test_idle_expiry_absolute_expiry_and_rolling_renewal(db_session):
    with real_authentication(), TestClient(app) as client:
        _login_admin(client, db_session)
        raw_token = client.cookies.get(get_settings().session_cookie_name)
        from app.core.security import session_digest

        session = db_session.scalar(
            select(AuthSession).where(AuthSession.token_digest == session_digest(raw_token))
        )
        assert session is not None
        previous_idle = utc_now() + timedelta(minutes=1)
        session.idle_expires_time = previous_idle
        session.last_seen_time = utc_now() - timedelta(days=1)
        db_session.commit()

        renewed = client.get("/api/v1/auth/me")
        assert renewed.status_code == 200
        db_session.expire_all()
        renewed_session = db_session.get(AuthSession, session.id)
        assert renewed_session.idle_expires_time > previous_idle.replace(tzinfo=None)

        renewed_session.idle_expires_time = utc_now() - timedelta(seconds=1)
        db_session.commit()
        idle_expired = client.get("/api/v1/auth/me")
        assert idle_expired.status_code == 401

    with real_authentication(), TestClient(app) as absolute_client:
        _login_admin(absolute_client, db_session)
        raw_token = absolute_client.cookies.get(get_settings().session_cookie_name)
        absolute_session = db_session.scalar(
            select(AuthSession).where(AuthSession.token_digest == session_digest(raw_token))
        )
        absolute_session.absolute_expires_time = utc_now() - timedelta(seconds=1)
        db_session.commit()
        absolute_expired = absolute_client.get("/api/v1/auth/me")
        assert absolute_expired.status_code == 401


def test_same_department_name_conflict_cross_department_allowed(db_session):
    with real_authentication(), TestClient(app) as admin_client:
        csrf = _login_admin(admin_client, db_session)
        departments = {
            item["name"]: item["id"]
            for item in admin_client.get("/api/v1/auth/departments").json()["data"]
        }

        def create_code(department_name: str) -> str:
            response = admin_client.post(
                "/api/v1/invitations",
                json={"department_id": departments[department_name]},
                headers={"X-CSRF-Token": csrf},
            )
            assert response.status_code == 201
            return response.json()["data"]["code"]

        first_code = create_code("运营部")
        duplicate_code = create_code("运营部")
        other_department_code = create_code("销售部")

        with TestClient(app) as client:
            first = client.post(
                "/api/v1/auth/registrations",
                json={
                    "department_id": departments["运营部"],
                    "name": " 同名用户 ",
                    "invitation_code": first_code,
                },
            )
            duplicate = client.post(
                "/api/v1/auth/registrations",
                json={
                    "department_id": departments["运营部"],
                    "name": "同名用户",
                    "invitation_code": duplicate_code,
                },
            )
            cross_department = client.post(
                "/api/v1/auth/registrations",
                json={
                    "department_id": departments["销售部"],
                    "name": "同名用户",
                    "invitation_code": other_department_code,
                },
            )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "AUTH_NAME_ALREADY_REGISTERED"
    assert cross_department.status_code == 201


def test_bootstrap_admin_is_one_time_only(db_session):
    with pytest.raises(ConflictError, match="已经存在"):
        AuthService(db_session).bootstrap_admin(
            department_name="产品部", user_name="第二管理员"
        )


def test_invitation_concurrent_use_creates_only_one_user(db_session):
    with real_authentication(), TestClient(app) as admin_client:
        csrf = _login_admin(admin_client, db_session)
        department = db_session.scalar(select(Department).where(Department.name == "运营部"))
        invitation = admin_client.post(
            "/api/v1/invitations",
            json={"department_id": department.id},
            headers={"X-CSRF-Token": csrf},
        ).json()["data"]
        barrier = Barrier(2)

        def register(name: str) -> tuple[int, str]:
            with TestClient(app) as client:
                barrier.wait()
                response = client.post(
                    "/api/v1/auth/registrations",
                    json={
                        "department_id": department.id,
                        "name": name,
                        "invitation_code": invitation["code"],
                    },
                )
                return response.status_code, response.json()["code"]

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(register, ("并发用户甲", "并发用户乙")))

    assert sorted(status for status, _ in results) == [201, 409]
    assert {code for _, code in results} == {"OK", "AUTH_INVITATION_USED"}
    created_count = db_session.scalar(
        select(func.count()).select_from(UserAccount).where(
            UserAccount.department_id == department.id,
            UserAccount.name.in_(["并发用户甲", "并发用户乙"]),
        )
    )
    assert created_count == 1
