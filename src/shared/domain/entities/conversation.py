"""Conversation domain entity.

Represents a chat conversation in the system domain, independent of
persistence concerns. This entity captures the business identity
and core attributes of a conversation.

The corresponding ORM model lives in:
    src.shared.infrastructure.persistence.database.models.Conversation
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.shared.kernel.base.entity import Entity


@dataclass(eq=False)
class ConversationEntity(Entity):
    """Domain entity for a chat conversation.

    Attributes:
        user_id: Owner's unique identifier.
        title: Conversation title.
        message_count: Denormalized message count for performance.
        last_message_at: Timestamp of the most recent message.
        created_at: Timestamp of creation.
    """

    user_id: UUID | None = None
    title: str = ""
    message_count: int = 0
    last_message_at: datetime | None = None
    created_at: datetime | None = None

    def __repr__(self) -> str:
        return f"ConversationEntity(id={self.id}, title={self.title!r})"