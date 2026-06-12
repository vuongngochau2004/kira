"""Document Module - Handles document upload, processing, and management.

This module provides functionality for:
- Document upload and storage
- Text extraction (PDF, DOCX, images with OCR fallback)
- Document cleaning and chunking
- Text embedding generation
- Document processing pipeline

Architecture:
- application: Use cases and DTOs
- domain: Business logic and services
- infrastructure: External adapters (OCR, storage)
- api: Request/response models
"""

from src.modules.document.application.upload import UploadDocument
from src.modules.document.application.delete import DeleteDocument
from src.modules.document.application.process import ProcessDocument
from src.modules.document.application.query import (
    DownloadDocument,
    GetDocument,
    GetDocumentChunks,
    ListDocuments,
)
from src.modules.document.application.dto import (
    UploadDocumentRequest,
    DeleteDocumentRequest,
    ProcessDocumentRequest,
    ListDocumentsRequest,
    GetDocumentRequest,
    DownloadDocumentRequest,
    GetDocumentChunksRequest,
    DocumentUploadResult,
    DocumentDeleteResult,
    DocumentProcessResult,
    DocumentListResult,
    DocumentGetResult,
    DocumentDownloadResult,
    DocumentChunksResult,
    DocumentMetadata,
)

__all__ = [
    # Application services
    "UploadDocument",
    "DeleteDocument",
    "ProcessDocument",
    "ListDocuments",
    "GetDocument",
    "DownloadDocument",
    "GetDocumentChunks",
    # DTOs
    "UploadDocumentRequest",
    "DeleteDocumentRequest",
    "ProcessDocumentRequest",
    "ListDocumentsRequest",
    "GetDocumentRequest",
    "DownloadDocumentRequest",
    "GetDocumentChunksRequest",
    "DocumentUploadResult",
    "DocumentDeleteResult",
    "DocumentProcessResult",
    "DocumentListResult",
    "DocumentGetResult",
    "DocumentDownloadResult",
    "DocumentChunksResult",
    "DocumentMetadata",
]
