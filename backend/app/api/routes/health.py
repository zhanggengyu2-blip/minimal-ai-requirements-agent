from pathlib import Path
from typing import Annotated

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse


router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
BACKEND_ROOT = Path(__file__).resolve().parents[3]
MIGRATION_HEAD = ScriptDirectory.from_config(
    Config(str(BACKEND_ROOT / "alembic.ini"))
).get_current_head()


@router.get("/health", response_model=ApiResponse[dict[str, str]])
def health(request: Request) -> ApiResponse[dict[str, str]]:
    return ApiResponse(data={"status": "ok"}, request_id=request.state.request_id)


@router.get(
    "/ready",
    response_model=ApiResponse[dict[str, str]],
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "数据库未连通或迁移未到最新版本"}},
)
def ready(request: Request, db: DbSession) -> ApiResponse[dict[str, str]]:
    try:
        current_revision = db.scalar(text("SELECT version_num FROM alembic_version"))
        db.scalar(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库连接或迁移状态不可用",
        ) from exc
    if not current_revision or current_revision != MIGRATION_HEAD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"数据库迁移未到最新版本：current={current_revision or 'none'}, head={MIGRATION_HEAD}",
        )
    return ApiResponse(
        data={"status": "ready", "migration_revision": current_revision},
        request_id=request.state.request_id,
    )
