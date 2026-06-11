"""DEPRECATED: Use src.shared.infrastructure.persistence.database.session instead."""

from src.shared.infrastructure.persistence.database.session import *  # noqa: F401,F403
from src.shared.infrastructure.persistence.database.session import (
    Base,
    engine,
    get_session,
    init_db,
    close_db,
    async_session_factory,
)

__all__ = [
    "Base",
    "engine",
    "get_session",
    "init_db",
    "close_db",
    "async_session_factory",
]
