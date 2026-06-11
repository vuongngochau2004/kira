"""API response models for Document module."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""

    document_id: UUID = Field(...)
    status: str = Field(...)
    message: str = Field(...)
    storage_path: str | None = Field(None)
    metadata: dict | None = Field(None)

    model_config = {"json_schema_extra": {"example": {
        "document_id": "123e4567-e89b-12d3-a456-426614174000",
        "status": "success",
        "message": "Document uploaded successfully",
        "storage_path": "user123/doc123/file.pdf",
        "metadata": {},
    }}}


class DocumentDeleteResponse(BaseModel):
    """Response model for document deletion."""

    document_id: UUID = Field(...)
    success: bool = Field(...)
    message: str = Field(...)

    model_config = {"json_schema_extra": {"example": {
        "document_id": "123e4567-e89b-12d3-a456-426614174000",
        "success": True,
        "message": "Document deleted successfully",
    }}}


class DocumentProcessResponse(BaseModel):
    """Response model for document processing."""

    document_id: UUID = Field(...)
    success: bool = Field(...)
    chunk_count: int | None = Field(None)
    error: str | None = Field(None)
    metadata: dict | None = Field(None)

    model_config = {"json_schema_extra": {"example": {
        "document_id": "123e4567-e89b-12d3-a456-426614174000",
        "success": True,
        "chunk_count": 42,
        "error": None,
        "metadata": {},
    }}}


class DocumentMetadata(BaseModel):
    """Document metadata response."""

    filename: str = Field(...)
    file_type: str = Field(...)
    user_id: str = Field(...)
    created_at: datetime = Field(...)
    status: str = Field(default="pending")
    chunk_count: int = Field(default=0)
    error_message: str | None = Field(None)
    extraction_method: str | None = Field(None)
    ocr_used: bool = Field(default=False)

    model_config = {"json_schema_extra": {"example": {
        "filename": "contract.pdf",
        "file_type": "pdf",
        "user_id": "user123",
        "created_at": "2026-06-11T12:00:00Z",
        "status": "completed",
        "chunk_count": 42,
        "error_message": None,
        "extraction_method": "pymupdf-ocr-hybrid",
        "ocr_used": True,
    }}}


__all__ = [
    "DocumentUploadResponse",
    "DocumentDeleteResponse",
    "DocumentProcessResponse",
    "DocumentMetadata",
]
