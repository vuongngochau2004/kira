"""Document processing application service."""

import logging
import uuid

from src.constants import DocumentStatus
from src.modules.document.application.dto import DocumentProcessResult, ProcessDocumentRequest
from src.modules.document.domain.services.pipeline import process_document
from src.shared.ports.document_repository import DocumentRepositoryPort
from src.shared.ports.embedding import EmbeddingPort
from src.shared.ports.keyword_index import KeywordIndexPort
from src.shared.ports.storage import StoragePort
from src.shared.ports.vector_store import VectorStorePort

logger = logging.getLogger(__name__)


class ProcessDocument:
    """Application service for running the document ingestion pipeline."""

    def __init__(
        self,
        repository: DocumentRepositoryPort,
        storage: StoragePort,
        embedding: EmbeddingPort,
        vector_store: VectorStorePort,
        keyword_index: KeywordIndexPort,
    ):
        """Initialize document processing service."""
        self.repository = repository
        self.storage = storage
        self.embedding = embedding
        self.vector_store = vector_store
        self.keyword_index = keyword_index

    async def execute(self, request: ProcessDocumentRequest) -> DocumentProcessResult:
        """Run document processing and update keyword indexes."""
        document_id = self._normalize_uuid(request.document_id)
        user_id = self._normalize_uuid(request.user_id)

        try:
            document = await self.repository.get_document(document_id=document_id, user_id=user_id)
            if not document or document.status == DocumentStatus.CANCELLED.value:
                logger.info("Skipping cancelled/missing document before processing: %s", document_id)
                return DocumentProcessResult(
                    document_id=document_id,
                    success=False,
                    error="Document processing cancelled",
                    metadata={"storage_path": request.storage_path, "cancelled": True},
                )

            processing_document = await self.repository.update_document_status(
                document_id=document_id,
                status=DocumentStatus.PROCESSING.value,
            )
            if not processing_document:
                logger.info("Skipping document after processing status update was rejected: %s", document_id)
                return DocumentProcessResult(
                    document_id=document_id,
                    success=False,
                    error="Document processing cancelled",
                    metadata={"storage_path": request.storage_path, "cancelled": True},
                )

            result = await process_document(
                document_id=document_id,
                user_id=user_id,
                storage_path=request.storage_path,
                storage=self.storage,
                embedding=self.embedding,
                vector_store=self.vector_store,
                repository=self.repository,
                timeout_seconds=request.timeout_seconds,
            )

            document = await self.repository.get_document(document_id=document_id, user_id=user_id)
            if not document or document.status == DocumentStatus.CANCELLED.value:
                logger.info("Skipping keyword index for cancelled document: %s", document_id)
                try:
                    await self.vector_store.delete_document(document_id)
                except Exception:
                    logger.warning(
                        "Failed to clean vector entries after cancellation for document %s",
                        document_id,
                        exc_info=True,
                    )
                return DocumentProcessResult(
                    document_id=document_id,
                    success=False,
                    error="Document processing cancelled",
                    metadata={"storage_path": request.storage_path, "cancelled": True},
                )

            if result["success"]:
                await self.keyword_index.add_document_bulk(
                    user_id=str(user_id),
                    chunks=result.get("chunks", []),
                )

            return DocumentProcessResult(
                document_id=document_id,
                success=result["success"],
                chunk_count=result.get("chunk_count"),
                error=result.get("error"),
                metadata={"storage_path": request.storage_path},
            )

        except Exception as e:
            logger.error("Failed to process document %s: %s", document_id, e, exc_info=True)
            await self.repository.update_document_status(
                document_id=document_id,
                status=DocumentStatus.FAILED.value,
                error_message=str(e),
            )
            return DocumentProcessResult(
                document_id=document_id,
                success=False,
                error=str(e),
                metadata={"storage_path": request.storage_path},
            )

    def _normalize_uuid(self, value: uuid.UUID | str) -> uuid.UUID:
        """Normalize UUID-like values."""
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


__all__ = ["ProcessDocument"]
