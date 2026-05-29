"""Indexing module exports."""

from src.indexing.qdrant_store import (
    get_client as get_qdrant_client,
    ensure_collection,
    store_chunks,
    search_similar,
    delete_document as delete_from_qdrant,
    close as close_qdrant,
)
from src.indexing.file_store import (
    get_client as get_minio_client,
    upload_file,
    upload_bytes,
    download_file,
    download_bytes,
    delete_file,
    get_presigned_url,
    file_exists,
    close as close_minio,
)
from src.indexing.document_store import (
    create_document,
    update_document_status,
    get_document,
    list_documents,
    delete_document,
    create_chunks,
    get_document_chunks,
    create_conversation,
    create_message,
    get_conversation_messages,
    list_conversations,
    get_conversation,
)

__all__ = [
    # Qdrant
    "get_qdrant_client",
    "ensure_collection",
    "store_chunks",
    "search_similar",
    "delete_from_qdrant",
    "close_qdrant",
    # MinIO
    "get_minio_client",
    "upload_file",
    "upload_bytes",
    "download_file",
    "download_bytes",
    "delete_file",
    "get_presigned_url",
    "file_exists",
    "close_minio",
    # Document Store
    "create_document",
    "update_document_status",
    "get_document",
    "list_documents",
    "delete_document",
    "create_chunks",
    "get_document_chunks",
    "create_conversation",
    "create_message",
    "get_conversation_messages",
    "list_conversations",
    "get_conversation",
]
