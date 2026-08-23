import argparse
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.core.exceptions import AppError
from app.services.auth_service import AuthService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the first administrator account")
    parser.add_argument("--department", required=True, help="Administrator department name")
    parser.add_argument("--name", required=True, help="Administrator display name")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        with SessionLocal() as db:
            user = AuthService(db).bootstrap_admin(
                department_name=args.department.strip(),
                user_name=args.name.strip(),
            )
    except AppError as exc:
        raise SystemExit(f"Administrator bootstrap refused: {exc.message}") from exc
    print(f"Administrator created: department={args.department.strip()}, name={user.name}")


if __name__ == "__main__":
    main()
