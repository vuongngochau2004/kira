"""SQLAlchemy adapter for identity user accounts."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.persistence.database.models import User


class SqlAlchemyUserAccountRepository:
    """Persistence adapter implementing the identity user-account port."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_email(self, email: str) -> User | None:
        result = await self._db.execute(
            select(User).where(User.email == email).where(User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_active_by_id(self, user_id: str) -> User | None:
        try:
            identifier = uuid.UUID(str(user_id))
        except ValueError:
            return None
        result = await self._db.execute(
            select(User)
            .where(User.id == identifier)
            .where(User.deleted_at.is_(None))
            .where(User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def create(self, *, email: str, hashed_password: str, full_name: str | None) -> Any:
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role="user",
            is_active=True,
        )
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)
        return user


__all__ = ["SqlAlchemyUserAccountRepository"]
