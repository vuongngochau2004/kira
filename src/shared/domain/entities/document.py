"""Document domain entity.

Represents a document in the system domain, independent of
persistence concerns (SQLAlchemy ORM models). This entity captures
the business identity and core attributes of a document.

The corresponding ORM model lives in:
    src.shared.infrastructure.persistence.database.models.Document
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.shared.kernel.base.entity import Entity


class DocumentStatus:
    """Document processing status (value object)."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(eq=False)
class DocumentEntity(Entity):
    """Domain entity for a user document.

    Attributes:
        filename: Original file name.
        user_id: Owner's unique identifier.
        file_type: MIME type of the file.
        file_size: Size in bytes.
        storage_path: Path in object storage (MinIO).
        status: Current processing status.
        chunk_count: Number of chunks after processing.
        created_at: Timestamp of creation.
        updated_at: Timestamp of last update.
    """

    filename: str = ""
    user_id: UUID | None = None
    file_type: str = ""
    file_size: int = 0
    storage_path: str = ""
    status: str = DocumentStatus.UPLOADING
    chunk_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __repr__(self) -> str:
        return f"DocumentEntity(id={self.id}, filename={self.filename!r})"