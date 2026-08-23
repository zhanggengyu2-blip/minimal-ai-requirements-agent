from sqlalchemy import func, select

from app.db.migrations import current_revision, upgrade_database
from app.db.models import Department
from app.db.seed import DEFAULT_DEPARTMENTS, seed_default_departments
from app.db.session import SessionLocal, engine


def test_database_is_at_v3_baseline() -> None:
    assert current_revision() == "0004_tasks_and_lanes"


def test_repeated_upgrade_preserves_seed_data() -> None:
    with SessionLocal() as db:
        before = db.scalar(select(func.count()).select_from(Department))

    upgrade_database()

    with SessionLocal() as db:
        after = db.scalar(select(func.count()).select_from(Department))
    assert before == after == len(DEFAULT_DEPARTMENTS)


def test_default_department_seed_is_idempotent() -> None:
    assert seed_default_departments() == 0
    with SessionLocal() as db:
        names = set(db.scalars(select(Department.name)).all())
    assert names == set(DEFAULT_DEPARTMENTS)


def test_sqlite_runtime_pragmas_are_enabled() -> None:
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one() == 5000
        assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one().lower() == "wal"
        assert connection.exec_driver_sql("PRAGMA synchronous").scalar_one() == 1
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
