from logging.config import fileConfig

from alembic import context

from app.config import get_settings
from app.db import create_db_engine
from app.models import Base

config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logging", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    # Tests pass their own URL; otherwise migrations use the direct connection.
    url = config.attributes.get("url") or get_settings().database_url_migrations
    if not url:
        raise RuntimeError("DATABASE_URL_MIGRATIONS is not set")
    return url


def run_migrations() -> None:
    engine = create_db_engine(get_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Offline migrations are not supported")

run_migrations()
