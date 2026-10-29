import os
import shutil
from pathlib import Path

import pytest


TEST_DB = Path(__file__).parent / "test_requirements.db"
TEST_UPLOAD_DIR = Path(__file__).parent / "test_uploads"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["DIFY_API_KEY"] = "test-key"
os.environ["INTERVIEW_IMAGE_STORAGE_DIR"] = str(TEST_UPLOAD_DIR)
os.environ["APP_ENV"] = "test"
os.environ["SHARED_PASSWORD"] = "test-shared-password"
os.environ["AUTH_HMAC_KEY"] = "test-hmac-key-0123456789abcdef0123456789"
os.environ["INVITATION_ENCRYPTION_KEY"] = "test-encryption-key-0123456789abcdef01"
os.environ["CSRF_ENABLED"] = "false"


@pytest.fixture(autouse=True)
def isolated_test_runtime():
    """Give every test a fresh database and attachment directory."""
    from app.db.migrations import upgrade_database
    from app.db.seed import seed_default_departments
    from app.db.session import engine
    from app.main import app
    from app.api.deps import get_auth_context
    from app.schemas.auth import SessionCreateRequest
    from app.services.auth_service import AuthService

    engine.dispose()
    TEST_DB.unlink(missing_ok=True)
    shutil.rmtree(TEST_UPLOAD_DIR, ignore_errors=True)
    upgrade_database(f"sqlite:///{TEST_DB}")
    seed_default_departments()
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        admin = AuthService(db).bootstrap_admin(
            department_name="产品部", user_name="测试管理员"
        )
        issued = AuthService(db).login(
            SessionCreateRequest(
                department_id=admin.department_id,
                name=admin.name,
                shared_password="test-shared-password",
            )
        )

    def override_auth_context():
        with SessionLocal() as db:
            return AuthService(db).resolve_session(issued.raw_token)

    app.dependency_overrides[get_auth_context] = override_auth_context
    yield
    app.dependency_overrides.clear()
    engine.dispose()
    TEST_DB.unlink(missing_ok=True)
    shutil.rmtree(TEST_UPLOAD_DIR, ignore_errors=True)


@pytest.fixture
def db_session():
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        yield db


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    TEST_DB.unlink(missing_ok=True)
    shutil.rmtree(TEST_UPLOAD_DIR, ignore_errors=True)
