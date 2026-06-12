"""Postgres document storage operations."""

import logging
from datetime import datetime
from uuid import UUID
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func


logger = logging.getLogger(__name__)


async def _get_session(db: AsyncSession | None) -> AsyncSession:
    """Get database session, create new one if not provided."""
    if db is None:
        from src.shared.infrastructure.persistence.database.session import async_session_factory
        return async_session_factory()
    return db


async def create_document(
    user_id: UUID,
    filename: str,
    file_type: str,
    file_size: int,
    storage_path: str,
    db: AsyncSession | None = None,
) -> Any:
    """Create a new document record.

    Args:
        user_id: User ID
        filename: Document filename
        file_type: File extension/type
        file_size: File size in bytes
        storage_path: Storage path (MinIO)
        db: Optional database session

    Returns:
        Document model instance
    """
    from src.shared.infrastructure.persistence.database.models import Document

    session = await _get_session(db)
    doc = Document(
        user_id=user_id,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        storage_path=storage_path,
        status="uploading",
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


async def update_document_status(
    document_id: UUID,
    status: str,
    error_message: str | None = None,
    chunk_count: int = 0,
    db: AsyncSession | None = None,
) -> Any | None:
    """Update document processing status.

    Args:
        document_id: Document ID
        status: New status (processing, completed, failed)
        error_message: Optional error message
        chunk_count: Number of chunks created
        db: Optional database session

    Returns:
        Updated document or None
    """
    from src.shared.infrastructure.persistence.database.models import Document

    session = await _get_session(db)
    values = {"status": status, "updated_at": datetime.utcnow()}

    if error_message is not None:
        values["error_message"] = error_message
    if chunk_count > 0:
        values["chunk_count"] = chunk_count

    result = await session.execute(
        update(Document)
        .where(Document.id == document_id)
        .where(Document.deleted_at.is_(None))
        .values(**values)
        .returning(Document)
    )
    await session.commit()
    return result.scalar_one_or_none()


async def get_document(
    document_id: UUID,
    user_id: UUID | None = None,
    db: AsyncSession | None = None,
) -> Any | None:
    """Get a document by ID.

    Args:
        document_id: Document ID
        user_id: Optional user ID filter
        db: Optional database session

    Returns:
        Document or None
    """
    from src.shared.infrastructure.persistence.database.models import Document

    session = await _get_session(db)
    query = select(Document).where(
        Document.id == document_id,
        Document.deleted_at.is_(None),
    )

    if user_id is not None:
        query = query.where(Document.user_id == user_id)

    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_documents_batch(
    document_ids: list[UUID | str],
    user_id: UUID | None = None,
    db: AsyncSession | None = None,
) -> dict[str, str]:
    """Batch fetch documents by IDs, returning {document_id: filename} mapping.

    Args:
        document_ids: List of document IDs to fetch
        user_id: Optional user ID filter
        db: Optional database session

    Returns:
        Dict mapping document_id (str) to filename
    """
    from src.shared.infrastructure.persistence.database.models import Document

    if not document_ids:
        return {}

    try:
        session = await _get_session(db)

        # Convert string IDs to UUID for query
        uuid_ids = []
        for doc_id in document_ids:
            if isinstance(doc_id, UUID):
                uuid_ids.append(doc_id)
            else:
                try:
                    uuid_id = UUID(doc_id)
                    uuid_ids.append(uuid_id)
                except ValueError:
                    continue  # Skip invalid UUIDs

        if not uuid_ids:
            return {}

        # Single batch query with WHERE IN clause
        query = select(Document).where(
            Document.id.in_(uuid_ids),
            Document.deleted_at.is_(None),
        )

        if user_id is not None:
            query = query.where(Document.user_id == user_id)

        result = await session.execute(query)
        documents = result.scalars().all()

        # Return {document_id: filename} mapping
        return {str(doc.id): doc.filename for doc in documents}

    except Exception as e:
        logger.error(f"Batch document query failed: {e}")
        return {}


async def list_documents(
    user_id: UUID,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession | None = None,
) -> tuple[list[Any], int]:
    """List user's documents.

    Args:
        user_id: User ID
        status: Optional status filter
        limit: Max results
        offset: Pagination offset
        db: Optional database session

    Returns:
        Tuple of (documents list, total count)
    """
    from src.shared.infrastructure.persistence.database.models import Document

    session = await _get_session(db)

    count_query = select(func.count()).select_from(Document).where(
        Document.user_id == user_id,
        Document.deleted_at.is_(None),
    )
    if status is not None:
        count_query = count_query.where(Document.status == status)

    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    query = (
        select(Document)
        .where(Document.user_id == user_id, Document.deleted_at.is_(None))
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if status is not None:
        query = query.where(Document.status == status)

    result = await session.execute(query)
    documents = result.scalars().all()

    return list(documents), total


async def delete_document(
    document_id: UUID,
    user_id: UUID,
    db: AsyncSession | None = None,
) -> bool:
    """Soft delete a document.

    Args:
        document_id: Document ID
        user_id: User ID
        db: Optional database session

    Returns:
        True if deleted, False otherwise
    """
    from src.shared.infrastructure.persistence.database.models import Document

    session = await _get_session(db)
    result = await session.execute(
        update(Document)
        .where(Document.id == document_id)
        .where(Document.user_id == user_id)
        .where(Document.deleted_at.is_(None))
        .values(deleted_at=datetime.utcnow())
        .returning(Document)
    )
    await session.commit()
    return result.scalar_one_or_none() is not None


async def create_deletion_retry_job(
    document_id: UUID,
    user_id: UUID,
    storage_path: str | None,
    cleanup_targets: list[str],
    last_error: str,
    db: AsyncSession | None = None,
) -> Any:
    """Create a retry job for failed document cleanup.

    Args:
        document_id: Document ID
        user_id: User ID
        storage_path: Object storage path, if any
        cleanup_targets: Failed cleanup targets to retry
        last_error: Error summary from the cleanup attempt
        db: Optional database session

    Returns:
        Created deletion retry job
    """
    from src.shared.infrastructure.persistence.database.models import DocumentDeletionJob

    session = await _get_session(db)
    job = DocumentDeletionJob(
        document_id=document_id,
        user_id=user_id,
        storage_path=storage_path,
        cleanup_targets=cleanup_targets,
        last_error=last_error,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def create_chunks(
    document_id: UUID,
    chunks: list[dict],
    db: AsyncSession | None = None,
) -> list[Any]:
    """Create document chunks.

    Args:
        document_id: Document ID
        chunks: List of chunk data
        db: Optional database session

    Returns:
        List of created chunk models
    """
    from src.shared.infrastructure.persistence.database.models import DocumentChunk

    session = await _get_session(db)
    chunk_models = []

    for chunk_data in chunks:
        chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=chunk_data["index"],
            content=chunk_data["content"],
            token_count=chunk_data.get("token_count", 0),
            metadata=chunk_data.get("metadata", {}),
            embedding_model=chunk_data.get("embedding_model", ""),
        )
        chunk_models.append(chunk)
        session.add(chunk)

    await session.commit()

    return chunk_models


async def get_document_chunks(
    document_id: UUID,
    db: AsyncSession | None = None,
) -> list[Any]:
    """Get all chunks for a document.

    Args:
        document_id: Document ID
        db: Optional database session

    Returns:
        List of chunks
    """
    from src.shared.infrastructure.persistence.database.models import DocumentChunk

    session = await _get_session(db)
    result = await session.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return list(result.scalars().all())


__all__ = [
    "create_document",
    "update_document_status",
    "get_document",
    "get_documents_batch",
    "list_documents",
    "delete_document",
    "create_deletion_retry_job",
    "create_chunks",
    "get_document_chunks",
]
