from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "极简AI团队需求管理智能体"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/requirements.db"

    dify_base_url: str = "http://127.0.0.1/v1"
    dify_api_key: str = ""
    dify_workflow_path: str = "/workflows/run"
    dify_timeout_seconds: float = Field(default=8.0, gt=0, le=300)
    dify_candidate_limit: int = Field(default=30, ge=0, le=100)
    dify_interview_api_key: str = ""
    dify_interview_workflow_path: str = "/workflows/run"
    dify_interview_timeout_seconds: float = Field(default=8.0, gt=0, le=300)
    dify_interview_prompt_version: str = "interview-prompt-v2.0.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

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
