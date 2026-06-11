"""Shared domain entities.

Domain entities extend the Entity base class from the shared kernel
and represent core business objects independent of persistence concerns.
"""

from src.shared.domain.entities.document import DocumentEntity, DocumentStatus
from src.shared.domain.entities.conversation import ConversationEntity
from src.shared.domain.entities.user import UserEntity, UserRole

__all__ = [
    "DocumentEntity",
    "DocumentStatus",
    "ConversationEntity",
    "UserEntity",
    "UserRole",
]