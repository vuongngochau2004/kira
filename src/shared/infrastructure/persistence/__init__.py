"""Shared persistence layer exports.

Provides database session management, ORM models, and query helpers
for PostgreSQL with async support.
"""

from src.shared.infrastructure.persistence.database.session import (
    Base,
    engine,
    get_session,
    init_db,
    close_db,
    async_session_factory,
)
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
from src.shared.infrastructure.persistence.database.query import (
    get_user_by_email,
    get_document_with_chunks,
    get_conversation_with_messages,
    list_user_documents,
    list_user_conversations,
    get_chunks_by_document,
    soft_delete_document,
    soft_delete_conversation,
)

__all__ = [
    # Session
    "Base",
    "engine",
    "get_session",
    "init_db",
    "close_db",
    "async_session_factory",
    # Models
    "User",
    "Document",
    "DocumentChunk",
    "Conversation",
    "Message",
    "UserRole",
    "DocumentStatus",
    "MessageRole",
    # Queries
    "get_user_by_email",
    "get_document_with_chunks",
    "get_conversation_with_messages",
    "list_user_documents",
    "list_user_conversations",
    "get_chunks_by_document",
    "soft_delete_document",
    "soft_delete_conversation",
]