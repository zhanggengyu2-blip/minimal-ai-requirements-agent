import os
from pathlib import Path


TEST_DB = Path(__file__).parent / "test_requirements.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["DIFY_API_KEY"] = "test-key"


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    TEST_DB.unlink(missing_ok=True)

