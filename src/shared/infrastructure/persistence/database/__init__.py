"""Persistence module - database and migration exports.

Re-exports all database session, model, and query symbols for convenience.
Import from src.shared.infrastructure.persistence.database for full access,
or from specific submodules for targeted imports.
"""

from src.shared.infrastructure.persistence.database.models import (
    Conversation,
    Document,
    DocumentChunk,
    DocumentStatus,
    Message,
    MessageRole,
    User,
    UserRole,
)
from src.shared.infrastructure.persistence.database.query import (
    get_chunks_by_document,
    get_conversation_with_messages,
    get_document_with_chunks,
    get_user_by_email,
    list_user_conversations,
    list_user_documents,
    soft_delete_conversation,
    soft_delete_document,
)
from src.shared.infrastructure.persistence.database.session import (
    Base,
    async_session_factory,
    close_db,
    engine,
    get_session,
    init_db,
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
