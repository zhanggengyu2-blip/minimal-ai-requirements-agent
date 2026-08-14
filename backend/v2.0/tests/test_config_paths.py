from pathlib import Path

from app.core.config import BACKEND_ROOT, Settings


def test_default_runtime_paths_are_anchored_to_backend_root(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("INTERVIEW_IMAGE_STORAGE_DIR", raising=False)

    settings = Settings(_env_file=None)

    assert settings.database_url == f"sqlite:///{BACKEND_ROOT / 'data/requirements.db'}"
    assert Path(settings.interview_image_storage_dir) == (
        BACKEND_ROOT / "data/uploads/interviews"
    )


def test_absolute_runtime_paths_are_preserved(tmp_path):
    database_path = tmp_path / "custom.db"
    upload_path = tmp_path / "uploads"

    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{database_path}",
        interview_image_storage_dir=str(upload_path),
    )

    assert settings.database_url == f"sqlite:///{database_path}"
    assert settings.interview_image_storage_dir == str(upload_path)
