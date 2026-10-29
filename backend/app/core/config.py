from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _backend_relative_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path.resolve()


def _resolve_sqlite_url(value: str) -> str:
    """让 SQLite 相对路径始终相对于 backend，而不是进程工作目录。"""
    prefix = "sqlite:///"
    if not value.startswith(prefix) or value.startswith("sqlite:////"):
        return value

    database_path = value.removeprefix(prefix)
    if database_path == ":memory:":
        return value
    return f"{prefix}{_backend_relative_path(database_path).as_posix()}"


class Settings(BaseSettings):
    app_name: str = "极简AI团队需求管理智能体"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/requirements.db"

    shared_password: str = ""
    auth_hmac_key: str = ""
    invitation_encryption_key: str = ""
    session_cookie_name: str = "team_session"
    session_cookie_secure: bool = False
    session_idle_days: int = Field(default=7, ge=1, le=30)
    session_absolute_days: int = Field(default=30, ge=1, le=365)
    csrf_header_name: str = "X-CSRF-Token"
    csrf_enabled: bool = True

    coo_base_url: str = "https://api.openai.com/v1"
    coo_api_key: str = ""
    coo_model: str = ""
    coo_timeout_seconds: float = Field(default=30, gt=0, le=120)
    coo_run_timeout_seconds: float = Field(default=90, gt=0, le=300)
    coo_max_rounds: int = Field(default=6, ge=1, le=12)
    coo_max_output_tokens: int = Field(default=1500, ge=128, le=4000)
    coo_token_budget: int = Field(default=48000, ge=2000, le=200000)
    coo_context_chars: int = Field(default=18000, ge=4000, le=60000)
    coo_event_poll_seconds: float = Field(default=2, ge=0.2, le=60)
    coo_event_max_attempts: int = Field(default=5, ge=1, le=10)
    coo_candidate_limit: int = Field(default=30, ge=0, le=100)

    knowledge_embedding_base_url: str = "https://api.openai.com/v1"
    knowledge_embedding_api_key: str = ""
    knowledge_embedding_model: str = ""
    knowledge_rerank_base_url: str = ""
    knowledge_rerank_api_key: str = ""
    knowledge_rerank_model: str = ""

    dify_base_url: str = "http://127.0.0.1/v1"
    dify_api_key: str = ""
    dify_workflow_path: str = "/workflows/run"
    dify_timeout_seconds: float = Field(default=8.0, gt=0, le=300)
    dify_candidate_limit: int = Field(default=30, ge=0, le=100)
    dify_interview_api_key: str = ""
    dify_interview_workflow_path: str = "/workflows/run"
    dify_interview_timeout_seconds: float = Field(default=8.0, gt=0, le=300)
    dify_interview_prompt_version: str = "interview-prompt-v2.0.1-image"
    dify_interview_image_input_name: str = "images"

    interview_image_storage_dir: str = "./data/uploads/interviews"
    interview_image_max_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    interview_image_max_count: int = Field(default=5, ge=1, le=10)

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        validate_default=True,
    )

    @field_validator("database_url")
    @classmethod
    def resolve_database_url(cls, value: str) -> str:
        return _resolve_sqlite_url(value)

    @field_validator("interview_image_storage_dir")
    @classmethod
    def resolve_interview_image_storage_dir(cls, value: str) -> str:
        return str(_backend_relative_path(value))

    @property
    def dify_workflow_url(self) -> str:
        return f"{self.dify_base_url.rstrip('/')}/{self.dify_workflow_path.lstrip('/')}"

    @property
    def dify_interview_workflow_url(self) -> str:
        return (
            f"{self.dify_base_url.rstrip('/')}/"
            f"{self.dify_interview_workflow_path.lstrip('/')}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
