"""User domain entity.

Represents a user in the system domain, independent of
persistence concerns. This entity captures the business identity
and core attributes of a user account.

The corresponding ORM model lives in:
    src.shared.infrastructure.persistence.database.models.User
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.shared.kernel.base.entity import Entity


class UserRole:
    """User role enumeration (value object)."""
    USER = "user"
    ADMIN = "admin"


@dataclass(eq=False)
class UserEntity(Entity):
    """Domain entity for a user account.

    Attributes:
        email: User's email address (unique).
        full_name: Display name.
        role: User role (user or admin).
        is_active: Whether the account is active.
        created_at: Timestamp of creation.
    """

    email: str = ""
    full_name: str = ""
    role: str = UserRole.USER
    is_active: bool = True
    created_at: datetime | None = None

    def __repr__(self) -> str:
        return f"UserEntity(id={self.id}, email={self.email!r})"