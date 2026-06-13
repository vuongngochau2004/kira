"""Document query application services."""

import mimetypes
import uuid

from src.modules.document.application.dto import (
    DocumentChunksResult,
    DocumentDownloadResult,
    DocumentGetResult,
    DocumentListResult,
    DownloadDocumentRequest,
    GetDocumentChunksRequest,
    GetDocumentRequest,
    ListDocumentsRequest,
)
from src.shared.ports.document_repository import DocumentRepositoryPort
from src.shared.ports.storage import StoragePort


class ListDocuments:
    """Application service for listing user documents."""

    def __init__(self, repository: DocumentRepositoryPort):
        """Initialize document listing service."""
        self.repository = repository

    async def execute(self, request: ListDocumentsRequest) -> DocumentListResult:
        """List documents owned by a user."""
        user_id = self._normalize_uuid(request.user_id)
        documents, total = await self.repository.list_documents(
            user_id=user_id,
            status=request.status,
            limit=request.limit,
            offset=request.offset,
        )

        return DocumentListResult(
            documents=documents,
            total=total,
            limit=request.limit,
            offset=request.offset,
        )

    def _normalize_uuid(self, value: uuid.UUID | str) -> uuid.UUID:
        """Normalize UUID-like values."""
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


class GetDocument:
    """Application service for fetching a user document."""

    def __init__(self, repository: DocumentRepositoryPort):
        """Initialize document fetching service."""
        self.repository = repository

    async def execute(self, request: GetDocumentRequest) -> DocumentGetResult:
        """Fetch a document owned by a user."""
        document = await self.repository.get_document(
            document_id=request.document_id,
            user_id=self._normalize_uuid(request.user_id),
        )
        return DocumentGetResult(document=document)

    def _normalize_uuid(self, value: uuid.UUID | str) -> uuid.UUID:
        """Normalize UUID-like values."""
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


class DownloadDocument:
    """Application service for downloading a document file."""

    def __init__(self, repository: DocumentRepositoryPort, storage: StoragePort):
        """Initialize document download service."""
        self.repository = repository
        self.storage = storage

    async def execute(self, request: DownloadDocumentRequest) -> DocumentDownloadResult | None:
        """Fetch document metadata and raw file bytes."""
        document = await self.repository.get_document(
            document_id=request.document_id,
            user_id=self._normalize_uuid(request.user_id),
        )
        if not document:
            return None

        file_bytes = await self.storage.download(document.storage_path)
        media_type, _ = mimetypes.guess_type(document.filename)

        return DocumentDownloadResult(
            filename=document.filename,
            file_bytes=file_bytes,
            media_type=media_type or "application/octet-stream",
        )

    def _normalize_uuid(self, value: uuid.UUID | str) -> uuid.UUID:
        """Normalize UUID-like values."""
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


class GetDocumentChunks:
    """Application service for fetching document chunks."""

    def __init__(self, repository: DocumentRepositoryPort):
        """Initialize document chunks service."""
        self.repository = repository

    async def execute(self, request: GetDocumentChunksRequest) -> DocumentChunksResult | None:
        """Fetch chunks for a document.

        Verifies the document exists (not deleted) without strict user ownership
        check, since the document_id originates from RAG retrieval which already
        filters results by user_id at the vector store level.
        """
        document = await self.repository.get_document(
            document_id=request.document_id,
        )
        if not document:
            return None

        chunks = await self.repository.get_document_chunks(document_id=request.document_id)

        return DocumentChunksResult(chunks=chunks)

    def _normalize_uuid(self, value: uuid.UUID | str) -> uuid.UUID:
        """Normalize UUID-like values."""
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


__all__ = [
    "ListDocuments",
    "GetDocument",
    "DownloadDocument",
    "GetDocumentChunks",
]
