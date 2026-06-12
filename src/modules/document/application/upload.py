"""Document upload application service."""

import asyncio
import logging
import uuid
from pathlib import Path

from src.modules.document.application.dto import (
    DocumentUploadResult,
    UploadDocumentRequest,
)
from src.shared.ports.document_repository import DocumentRepositoryPort
from src.shared.ports.storage import StoragePort

logger = logging.getLogger(__name__)


class UploadDocument:
    """Application service for storing an uploaded document and creating metadata."""

    def __init__(
        self,
        repository: DocumentRepositoryPort,
        storage: StoragePort,
    ):
        """Initialize document upload service.

        Args:
            repository: Document metadata repository
            storage: Object storage adapter
        """
        self.repository = repository
        self.storage = storage

    async def execute(self, request: UploadDocumentRequest) -> DocumentUploadResult:
        """Store document bytes or a local file and create the document record.

        Args:
            request: Upload document request

        Returns:
            Document upload result
        """
        logger.info("Uploading document: %s for user: %s", request.file_name, request.user_id)

        try:
            if request.file_content is None and request.file_path is None:
                return DocumentUploadResult(
                    document_id=uuid.uuid4(),
                    status="failed",
                    message="Either file_content or file_path is required",
                )

            storage_path = self._generate_storage_path(
                user_id=request.user_id,
                file_name=request.file_name,
            )

            file_size = request.file_size
            if request.file_content is not None:
                file_size = len(request.file_content)
                await self.storage.upload(
                    key=storage_path,
                    data=request.file_content,
                    content_type=request.content_type or "application/octet-stream",
                )
            else:
                file_path = Path(request.file_path or "")
                if not file_path.exists():
                    return DocumentUploadResult(
                        document_id=uuid.uuid4(),
                        status="failed",
                        message=f"File not found: {request.file_path}",
                    )

                file_size = file_size if file_size is not None else file_path.stat().st_size
                data = await asyncio.to_thread(file_path.read_bytes)
                await self.storage.upload(
                    key=storage_path,
                    data=data,
                    content_type=request.content_type or "application/octet-stream",
                )

            logger.info("File uploaded to storage: %s", storage_path)

            document = await self.repository.create_document(
                user_id=self._normalize_uuid(request.user_id),
                filename=request.file_name,
                file_type=request.file_type,
                file_size=file_size or 0,
                storage_path=storage_path,
            )

            return DocumentUploadResult(
                document_id=document.id,
                status="success",
                message="Document uploaded successfully",
                storage_path=storage_path,
                metadata={"filename": request.file_name, "file_size": file_size or 0},
                document=document,
            )

        except Exception as e:
            logger.error("Failed to upload document: %s", e, exc_info=True)
            return DocumentUploadResult(
                document_id=uuid.uuid4(),
                status="failed",
                message=f"Upload failed: {str(e)}",
            )

    def _generate_storage_path(self, user_id: uuid.UUID | str, file_name: str) -> str:
        """Generate storage path for document.

        Args:
            user_id: User ID
            file_name: Original file name

        Returns:
            Storage path string
        """
        user_id_str = str(user_id) if isinstance(user_id, uuid.UUID) else user_id
        file_ext = Path(file_name).suffix.lstrip(".") or "txt"

        return f"{user_id_str}/{uuid.uuid4()}.{file_ext}"

    def _normalize_uuid(self, value: uuid.UUID | str) -> uuid.UUID:
        """Normalize UUID-like values."""
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


__all__ = ["UploadDocument"]
