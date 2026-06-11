"""API request models for Document module."""

from uuid import UUID
from pydantic import BaseModel, Field


class UploadDocumentRequest(BaseModel):
    """Request model for document upload."""

    file_name: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    file_type: str = Field(..., min_length=1, max_length=50)


class DeleteDocumentRequest(BaseModel):
    """Request model for document deletion."""

    document_id: UUID = Field(...)
    user_id: str = Field(..., min_length=1)


class ProcessDocumentRequest(BaseModel):
    """Request model for document processing."""

    document_id: UUID = Field(...)
    user_id: str = Field(..., min_length=1)
    storage_path: str = Field(..., min_length=1)
    timeout_seconds: int = Field(default=600, ge=1, le=3600)


__all__ = [
    "UploadDocumentRequest",
    "DeleteDocumentRequest",
    "ProcessDocumentRequest",
]
