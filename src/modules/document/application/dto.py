"""Data Transfer Objects for Document module."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class UploadDocumentRequest:
    """Request DTO for document upload."""

    file_name: str
    user_id: UUID | str
    file_type: str
    file_content: bytes | None = None
    file_path: str | None = None
    file_size: int | None = None
    content_type: str | None = None


@dataclass(frozen=True)
class DeleteDocumentRequest:
    """Request DTO for document deletion."""

    document_id: UUID
    user_id: UUID | str


@dataclass(frozen=True)
class CancelDocumentRequest:
    """Request DTO for document cancellation."""

    document_id: UUID
    user_id: UUID | str


@dataclass(frozen=True)
class ProcessDocumentRequest:
    """Request DTO for document processing."""

    document_id: UUID
    user_id: UUID | str
    storage_path: str
    timeout_seconds: int = 600


@dataclass(frozen=True)
class ListDocumentsRequest:
    """Request DTO for listing documents."""

    user_id: UUID | str
    status: str | None = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetDocumentRequest:
    """Request DTO for fetching a document."""

    document_id: UUID
    user_id: UUID | str


@dataclass(frozen=True)
class DownloadDocumentRequest:
    """Request DTO for downloading a document."""

    document_id: UUID
    user_id: UUID | str


@dataclass(frozen=True)
class GetDocumentChunksRequest:
    """Request DTO for fetching document chunks."""

    document_id: UUID
    user_id: UUID | str


@dataclass(frozen=True)
class DocumentUploadResult:
    """Result DTO for document upload."""

    document_id: UUID
    status: str
    message: str
    storage_path: str | None = None
    metadata: dict[str, Any] | None = None
    document: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "document_id": str(self.document_id),
            "status": self.status,
            "message": self.message,
            "storage_path": self.storage_path,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class DocumentDeleteResult:
    """Result DTO for document deletion."""

    document_id: UUID
    success: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "document_id": str(self.document_id),
            "success": self.success,
            "message": self.message,
        }


@dataclass(frozen=True)
class DocumentCancelResult:
    """Result DTO for document cancellation."""

    document_id: UUID
    success: bool
    message: str
    status: str | None = None
    cleanup_errors: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "document_id": str(self.document_id),
            "success": self.success,
            "message": self.message,
            "status": self.status,
            "cleanup_errors": self.cleanup_errors,
        }


@dataclass(frozen=True)
class DocumentProcessResult:
    """Result DTO for document processing."""

    document_id: UUID
    success: bool
    chunk_count: int | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "document_id": str(self.document_id),
            "success": self.success,
            "chunk_count": self.chunk_count,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class DocumentListResult:
    """Result DTO for document listing."""

    documents: list[Any]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class DocumentGetResult:
    """Result DTO for document fetching."""

    document: Any | None


@dataclass(frozen=True)
class DocumentDownloadResult:
    """Result DTO for document download."""

    filename: str
    file_bytes: bytes
    media_type: str


@dataclass(frozen=True)
class DocumentChunksResult:
    """Result DTO for document chunks."""

    chunks: list[Any]


@dataclass(frozen=True)
class DocumentMetadata:
    """Document metadata value object."""

    filename: str
    file_type: str
    user_id: UUID | str
    created_at: datetime
    status: str = "pending"
    chunk_count: int = 0
    error_message: str | None = None
    extraction_method: str | None = None
    ocr_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "filename": self.filename,
            "file_type": self.file_type,
            "user_id": str(self.user_id) if isinstance(self.user_id, UUID) else self.user_id,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "chunk_count": self.chunk_count,
            "error_message": self.error_message,
            "extraction_method": self.extraction_method,
            "ocr_used": self.ocr_used,
        }


__all__ = [
    "UploadDocumentRequest",
    "CancelDocumentRequest",
    "DeleteDocumentRequest",
    "ProcessDocumentRequest",
    "ListDocumentsRequest",
    "GetDocumentRequest",
    "DownloadDocumentRequest",
    "GetDocumentChunksRequest",
    "DocumentUploadResult",
    "DocumentCancelResult",
    "DocumentDeleteResult",
    "DocumentProcessResult",
    "DocumentListResult",
    "DocumentGetResult",
    "DocumentDownloadResult",
    "DocumentChunksResult",
    "DocumentMetadata",
]
