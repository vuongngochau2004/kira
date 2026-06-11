"""DEPRECATED: Use src.shared.infrastructure.persistence.database.models instead."""

from src.shared.infrastructure.persistence.database.models import (
    User,
    Document,
    DocumentChunk,
    Conversation,
    Message,
    UserRole,
    DocumentStatus,
    MessageRole,
)

__all__ = [
    "User",
    "Document",
    "DocumentChunk",
    "Conversation",
    "Message",
    "UserRole",
    "DocumentStatus",
    "MessageRole",
]
