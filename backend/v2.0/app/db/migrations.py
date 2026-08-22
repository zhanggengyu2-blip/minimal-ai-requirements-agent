from alembic import command
from alembic.config import Config

from app.core.config import BACKEND_ROOT, get_settings


def build_alembic_config(database_url: str | None = None) -> Config:
    config_path = BACKEND_ROOT / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    config.attributes["database_url"] = database_url or get_settings().database_url
    return config


def upgrade_database(database_url: str | None = None) -> None:
    """Upgrade one explicitly selected database to the latest schema revision."""
    command.upgrade(build_alembic_config(database_url), "head")


def current_revision(database_url: str | None = None) -> str | None:
    """Return the current revision without parsing Alembic's console output."""
    from sqlalchemy import create_engine, inspect, text

    url = database_url or get_settings().database_url
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            if not inspect(connection).has_table("alembic_version"):
                return None
            return connection.scalar(text("SELECT version_num FROM alembic_version"))
    finally:
        engine.dispose()
