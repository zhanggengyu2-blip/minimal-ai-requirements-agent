import argparse

from app.db.session import SessionLocal
from app.services.auth_service import AuthService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the first administrator account")
    parser.add_argument("--department", required=True, help="Administrator department name")
    parser.add_argument("--name", required=True, help="Administrator display name")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with SessionLocal() as db:
        user = AuthService(db).bootstrap_admin(
            department_name=args.department.strip(),
            user_name=args.name.strip(),
        )
    print(f"Administrator created: department={args.department.strip()}, name={user.name}")


if __name__ == "__main__":
    main()
