"""Composition root for identity use cases."""

from sqlalchemy.ext.asyncio import AsyncSession

from kira.auth.repository import SqlAlchemyUserAccountRepository
from kira.auth.security import hash_password, verify_password
from kira.auth.service import IdentityService


def identity_service(db: AsyncSession) -> IdentityService:
    """Compose an identity service for one request transaction."""
    return IdentityService(
        users=SqlAlchemyUserAccountRepository(db),
        hash_password=hash_password,
        verify_password=verify_password,
    )


__all__ = ["identity_service"]
