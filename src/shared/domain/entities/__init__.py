"""Shared domain entities.

Domain entities extend the Entity base class from the shared kernel
and represent core business objects independent of persistence concerns.
"""

from src.shared.domain.entities.document import DocumentEntity
from src.shared.domain.entities.conversation import ConversationEntity
from src.shared.domain.entities.user import UserEntity

__all__ = [
    "DocumentEntity",
    "ConversationEntity",
    "UserEntity",
]