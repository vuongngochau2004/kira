"""Composition root for identity use cases."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application import IdentityService
from src.modules.identity.infrastructure.user_repository import SqlAlchemyUserAccountRepository
from src.shared.infrastructure.auth.security import hash_password, verify_password


def identity_service(db: AsyncSession) -> IdentityService:
    """Compose an identity service for one request transaction."""
    return IdentityService(
        users=SqlAlchemyUserAccountRepository(db),
        hash_password=hash_password,
        verify_password=verify_password,
    )


__all__ = ["identity_service"]
