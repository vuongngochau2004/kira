"""API layer for Document module.

Contains request and response models for document operations.
"""

from src.modules.document.api.requests import (
    DeleteDocumentRequest,
    ProcessDocumentRequest,
    UploadDocumentRequest,
)
from src.modules.document.api.responses import (
    DocumentDeleteResponse,
    DocumentMetadata,
    DocumentProcessResponse,
    DocumentUploadResponse,
)

__all__ = [
    "UploadDocumentRequest",
    "DeleteDocumentRequest",
    "ProcessDocumentRequest",
    "DocumentUploadResponse",
    "DocumentDeleteResponse",
    "DocumentProcessResponse",
    "DocumentMetadata",
]
