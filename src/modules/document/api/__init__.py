"""API layer for Document module.

Contains request and response models for document operations.
"""

from src.modules.document.api.requests import (
    UploadDocumentRequest,
    DeleteDocumentRequest,
    ProcessDocumentRequest,
)
from src.modules.document.api.responses import (
    DocumentUploadResponse,
    DocumentDeleteResponse,
    DocumentProcessResponse,
    DocumentMetadata,
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
