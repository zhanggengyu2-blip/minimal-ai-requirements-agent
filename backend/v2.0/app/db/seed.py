from sqlalchemy import func, select

from app.db.models import Department
from app.db.session import SessionLocal


DEFAULT_DEPARTMENTS = ("运营部", "产品部", "销售部")


def seed_default_departments() -> int:
    """Insert missing built-in departments and return the number created."""
    with SessionLocal.begin() as db:
        existing_names = set(db.scalars(select(Department.name)).all())
        missing_names = [name for name in DEFAULT_DEPARTMENTS if name not in existing_names]
        db.add_all(Department(name=name) for name in missing_names)
        return len(missing_names)


def main() -> None:
    created = seed_default_departments()
    with SessionLocal() as db:
        total = db.scalar(select(func.count()).select_from(Department))
    print(f"Seed complete: created={created}, departments={total or 0}")


if __name__ == "__main__":
    main()
