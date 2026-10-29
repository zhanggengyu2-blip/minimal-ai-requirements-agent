from datetime import datetime, timezone
from typing import Literal
from pydantic import ConfigDict, Field, field_validator
from app.schemas.common import ORMModel

class TaskCommentCreate(ORMModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=4000)
    parent_id: str | None = Field(default=None, min_length=32, max_length=32)

    @field_validator("content")
    @classmethod
    def clean_content(cls, value):
        if not value.strip():
            raise ValueError("留言不能为空")
        return value.strip()

class TaskCommentRead(ORMModel):
    id: str
    project_id: str
    task_id: str
    author_id: str
    author_name: str
    actor_type: Literal["HUMAN", "COO"]
    parent_id: str | None
    content: str
    agent_run_id: str | None
    created_time: datetime

    @field_validator('created_time')
    @classmethod
    def utc_created_time(cls, value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
