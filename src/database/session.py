"""Async database session and engine configuration."""

import sys
from collections.abc import AsyncGenerator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config.config import settings

DEFAULT_POOL_SIZE = 20
DEFAULT_MAX_OVERFLOW = 40
DEFAULT_POOL_RECYCLE = 3600


engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=DEFAULT_POOL_SIZE,
    max_overflow=DEFAULT_MAX_OVERFLOW,
    pool_recycle=DEFAULT_POOL_RECYCLE,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection and create tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
