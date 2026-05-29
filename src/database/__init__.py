"""Database layer exports."""

from src.database.session import Base, engine, get_session, init_db, close_db
from src.database.models import User, Document, DocumentChunk, Conversation, Message
from src.database.query import (
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
    # Models
    "User",
    "Document",
    "DocumentChunk",
    "Conversation",
    "Message",
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
