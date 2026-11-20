"""Dependency composition for the document module."""

from sqlalchemy.ext.asyncio import AsyncSession

from kira.documents.cancel import CancelDocument
from kira.documents.delete import DeleteDocument
from kira.documents.process import ProcessDocument
from kira.documents.repository_adapter import SqlAlchemyDocumentRepository
from kira.documents.task_queue import CeleryTaskQueueAdapter
from kira.documents.upload import UploadDocument
from kira.providers.embedding.base import EmbeddingPort
from kira.providers.embedding.factory import create_embedding_adapter
from kira.providers.ocr import PaddleOCR
from kira.providers.storage import MinioStorage
from kira.providers.vector_store import QdrantVectorStore
from kira.retrieval.bm25_adapter import BM25KeywordIndexAdapter
from kira.retrieval.bm25_manager import get_bm25_manager


def document_repository(db: AsyncSession) -> SqlAlchemyDocumentRepository:
    """Create request-scoped document repository adapter."""
    return SqlAlchemyDocumentRepository(db=db)


def storage_adapter() -> MinioStorage:
    """Create object storage adapter."""
    return MinioStorage()


def embedding_adapter() -> EmbeddingPort:
    """Create embedding adapter."""
    return create_embedding_adapter()


def vector_store_adapter() -> QdrantVectorStore:
    """Create vector store adapter."""
    return QdrantVectorStore()


def ocr_adapter() -> PaddleOCR:
    return PaddleOCR()


def keyword_index_adapter() -> BM25KeywordIndexAdapter:
    """Create keyword index adapter."""
    return BM25KeywordIndexAdapter(manager=get_bm25_manager())


def task_queue_adapter() -> CeleryTaskQueueAdapter:
    """Create the background-job adapter used by document use cases."""
    return CeleryTaskQueueAdapter()


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
        ocr=ocr_adapter(),
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
        task_queue=task_queue_adapter(),
    )


__all__ = [
    "cancel_document_service",
    "delete_document_service",
    "document_repository",
    "embedding_adapter",
    "keyword_index_adapter",
    "ocr_adapter",
    "process_document_service",
    "storage_adapter",
    "task_queue_adapter",
    "upload_document_service",
    "vector_store_adapter",
]
