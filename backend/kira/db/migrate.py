"""Apply Alembic migrations at startup.

A database created before Alembic was introduced (tables exist, no alembic_version)
is stamped at the baseline revision first, then upgraded normally.
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, inspect

from kira.db.session import engine

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
BASELINE_REVISION = "0001"


def _alembic_config(connection: Connection) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.attributes["connection"] = connection
    config.attributes["configure_logger"] = False
    return config


def _upgrade(connection: Connection) -> None:
    config = _alembic_config(connection)
    tables = set(inspect(connection).get_table_names())
    if "alembic_version" not in tables and "users" in tables:
        logger.warning(
            "Existing schema has no Alembic history; stamping baseline %s", BASELINE_REVISION
        )
        command.stamp(config, BASELINE_REVISION)
    command.upgrade(config, "head")


async def run_migrations() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(_upgrade)
