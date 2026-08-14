import os
import shutil
from pathlib import Path


TEST_DB = Path(__file__).parent / "test_requirements.db"
TEST_UPLOAD_DIR = Path(__file__).parent / "test_uploads"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["DIFY_API_KEY"] = "test-key"
os.environ["INTERVIEW_IMAGE_STORAGE_DIR"] = str(TEST_UPLOAD_DIR)


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    TEST_DB.unlink(missing_ok=True)
    shutil.rmtree(TEST_UPLOAD_DIR, ignore_errors=True)
