"""Document upload use case for application layer."""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from src.modules.document.application.dto import (
    DocumentMetadata,
    DocumentUploadResult,
    UploadDocumentRequest,
)
from src.modules.document.infrastructure.storage.storage import upload_file
from src.shared.domain.entities import DocumentEntity

logger = logging.getLogger(__name__)


class UploadDocumentUseCase:
    """Use case for uploading documents."""

    def __init__(self, file_store_client: Any = None):
        """Initialize upload document use case.

        Args:
            file_store_client: Optional file store client (for dependency injection)
        """
        self.file_store_client = file_store_client

    async def execute(self, request: UploadDocumentRequest) -> DocumentUploadResult:
        """Execute document upload use case.

        Args:
            request: Upload document request

        Returns:
            Document upload result
        """
        logger.info("Uploading document: %s for user: %s", request.file_name, request.user_id)

        try:
            # Validate file exists
            file_path = Path(request.file_path)
            if not file_path.exists():
                return DocumentUploadResult(
                    document_id=uuid.uuid4(),
                    status="failed",
                    message=f"File not found: {request.file_path}",
                )

            # Generate document ID
            document_id = uuid.uuid4()

            # Generate storage path
            storage_path = self._generate_storage_path(
                user_id=request.user_id,
                document_id=document_id,
                file_name=request.file_name,
            )

            # Upload file to storage
            upload_file(
                file_path=request.file_path,
                object_name=storage_path,
            )

            logger.info("File uploaded to storage: %s", storage_path)

            # Create document metadata
            metadata = DocumentMetadata(
                filename=request.file_name,
                file_type=request.file_type,
                user_id=request.user_id,
                created_at=datetime.utcnow(),
                status="pending",
            )

            # Create document entity (would be saved to database in full implementation)
            document_entity = DocumentEntity(
                id=document_id,
                filename=request.file_name,
                user_id=str(request.user_id) if isinstance(request.user_id, uuid.UUID) else request.user_id,
                created_at=datetime.utcnow(),
                storage_path=storage_path,
                status="pending",
                metadata=metadata.to_dict(),
            )

            return DocumentUploadResult(
                document_id=document_id,
                status="success",
                message="Document uploaded successfully",
                storage_path=storage_path,
                metadata={
                    "document": document_entity.to_dict() if hasattr(document_entity, 'to_dict') else {},
                },
            )

        except Exception as e:
            logger.error("Failed to upload document: %s", e, exc_info=True)
            return DocumentUploadResult(
                document_id=uuid.uuid4(),
                status="failed",
                message=f"Upload failed: {str(e)}",
            )

    def _generate_storage_path(self, user_id: uuid.UUID | str, document_id: uuid.UUID, file_name: str) -> str:
        """Generate storage path for document.

        Args:
            user_id: User ID
            document_id: Document ID
            file_name: Original file name

        Returns:
            Storage path string
        """
        user_id_str = str(user_id) if isinstance(user_id, uuid.UUID) else user_id
        document_id_str = str(document_id)

        # Generate path: {user_id}/{document_id}/{original_filename}
        # This organizes files by user and document
        safe_filename = Path(file_name).name
        return f"{user_id_str}/{document_id_str}/{safe_filename}"


__all__ = ["UploadDocumentUseCase"]
