"""DEPRECATED: Use src.shared.infrastructure.persistence.database.query instead."""

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
    "get_user_by_email",
    "get_document_with_chunks",
    "get_conversation_with_messages",
    "list_user_documents",
    "list_user_conversations",
    "get_chunks_by_document",
    "soft_delete_document",
    "soft_delete_conversation",
]
