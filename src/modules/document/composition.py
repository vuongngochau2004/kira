"""Dependency composition for the document module."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.document.application import CancelDocument, DeleteDocument, ProcessDocument, UploadDocument
from src.modules.document.infrastructure.document_repository import SqlAlchemyDocumentRepository
from src.modules.retrieval.infrastructure.keyword.bm25_adapter import BM25KeywordIndexAdapter
from src.modules.retrieval.infrastructure.keyword.bm25_manager import get_bm25_manager
from src.shared.adapters.embedding.api_adapter import EmbeddingAPIAdapter
from src.shared.adapters.storage.minio_adapter import MinIOAdapter
from src.shared.adapters.vector.qdrant_adapter import QdrantAdapter


def document_repository(db: AsyncSession) -> SqlAlchemyDocumentRepository:
    """Create request-scoped document repository adapter."""
    return SqlAlchemyDocumentRepository(db=db)


def storage_adapter() -> MinIOAdapter:
    """Create object storage adapter."""
    return MinIOAdapter()


def embedding_adapter() -> EmbeddingAPIAdapter:
    """Create embedding adapter."""
    return EmbeddingAPIAdapter()


def vector_store_adapter() -> QdrantAdapter:
    """Create vector store adapter."""
    return QdrantAdapter()


def keyword_index_adapter() -> BM25KeywordIndexAdapter:
    """Create keyword index adapter."""
    return BM25KeywordIndexAdapter(manager=get_bm25_manager())


def upload_document_service(db: AsyncSession) -> UploadDocument:
    """Compose upload application service."""
    return UploadDocument(
        repository=document_repository(db),
        storage=storage_adapter(),
    )


def process_document_service(db: AsyncSession) -> ProcessDocument:
    """Compose processing application service."""
    return ProcessDocument(
        repository=document_repository(db),
        storage=storage_adapter(),
        embedding=embedding_adapter(),
        vector_store=vector_store_adapter(),
        keyword_index=keyword_index_adapter(),
    )


def delete_document_service(db: AsyncSession) -> DeleteDocument:
    """Compose deletion application service."""
    return DeleteDocument(
        repository=document_repository(db),
        keyword_index=keyword_index_adapter(),
        vector_store=vector_store_adapter(),
        storage=storage_adapter(),
    )


def cancel_document_service(db: AsyncSession) -> CancelDocument:
    """Compose cancellation application service."""
    return CancelDocument(
        repository=document_repository(db),
        keyword_index=keyword_index_adapter(),
        vector_store=vector_store_adapter(),
        storage=storage_adapter(),
    )


__all__ = [
    "cancel_document_service",
    "delete_document_service",
    "document_repository",
    "embedding_adapter",
    "keyword_index_adapter",
    "process_document_service",
    "storage_adapter",
    "upload_document_service",
    "vector_store_adapter",
]
