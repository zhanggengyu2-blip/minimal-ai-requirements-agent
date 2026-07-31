from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()

if settings.database_url.startswith("sqlite:///./"):
    Path(settings.database_url.removeprefix("sqlite:///./")).parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from sqlalchemy import func, select

    from app.db import models
    from app.db.base import Base

    Base.metadata.create_all(bind=engine)
    _migrate_v2_sqlite_requirement_columns()
    with SessionLocal() as db:
        if (db.scalar(select(func.count()).select_from(models.Department)) or 0) == 0:
            db.add_all(
                [
                    models.Department(name="运营部"),
                    models.Department(name="产品部"),
                    models.Department(name="销售部"),
                ]
            )
            db.commit()


def _migrate_v2_sqlite_requirement_columns() -> None:
    """V1.1 SQLite 轻量升级。新表由 create_all 创建，这里只补主表字段。"""
    if not settings.database_url.startswith("sqlite"):
        return

    additions = {
        "interview_session_id": "VARCHAR(32)",
        "clarified_content": "TEXT",
        "interview_rounds": "INTEGER NOT NULL DEFAULT 0",
        "completeness_score": "INTEGER",
    }
    with engine.begin() as connection:
        columns = {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(requirement)").all()
        }
        for name, ddl in additions.items():
            if name not in columns:
                connection.exec_driver_sql(f"ALTER TABLE requirement ADD COLUMN {name} {ddl}")
        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "ux_requirement_interview_session_id "
            "ON requirement (interview_session_id)"
        )
