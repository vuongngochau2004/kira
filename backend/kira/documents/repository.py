"""All SQL for documents and chunks: module functions plus the session-bound DocumentRepository."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _get_session(db: AsyncSession | None) -> AsyncSession:
    """Get database session, create new one if not provided."""
    if db is None:
        from kira.db.session import async_session_factory

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
    from kira.db.models import Document

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
    from kira.db.models import Document

    session = await _get_session(db)
    values = {"status": status, "updated_at": datetime.utcnow()}

    if error_message is not None:
        values["error_message"] = error_message
    elif status != "failed":
        # A reprocessed document leaving the failed state must not keep the old run's error.
        values["error_message"] = None
    if chunk_count > 0:
        values["chunk_count"] = chunk_count

    result = await session.execute(
        update(Document)
        .where(Document.id == document_id)
        .where(Document.deleted_at.is_(None))
        .where(Document.status != "cancelled")
        .values(**values)
        .returning(Document)
    )
    await session.commit()
    return result.scalar_one_or_none()


async def update_document_processing_task(
    document_id: UUID,
    task_id: str | None,
    db: AsyncSession | None = None,
) -> Any | None:
    """Store the Celery task ID used to process a document."""
    from kira.db.models import Document

    session = await _get_session(db)
    result = await session.execute(
        update(Document)
        .where(Document.id == document_id)
        .where(Document.deleted_at.is_(None))
        .values(processing_task_id=task_id, updated_at=datetime.utcnow())
        .returning(Document)
    )
    await session.commit()
    return result.scalar_one_or_none()


async def cancel_document(
    document_id: UUID,
    user_id: UUID,
    reason: str | None = None,
    db: AsyncSession | None = None,
) -> Any | None:
    """Mark an in-progress document as cancelled."""
    from kira.db.models import Document

    session = await _get_session(db)
    result = await session.execute(
        update(Document)
        .where(Document.id == document_id)
        .where(Document.user_id == user_id)
        .where(Document.deleted_at.is_(None))
        .where(Document.status.in_(["uploading", "processing", "failed"]))
        .values(
            status="cancelled",
            error_message=reason or "Processing cancelled by user",
            updated_at=datetime.utcnow(),
        )
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
    from kira.db.models import Document

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
    from kira.db.models import Document

    if not document_ids:
        return {}

    try:
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

        async def _execute_query(session: AsyncSession) -> dict[str, str]:
            result = await session.execute(query)
            documents = result.scalars().all()
            return {str(doc.id): doc.filename for doc in documents}

        if db is not None:
            return await _execute_query(db)

        from kira.db.session import async_session_factory

        async with async_session_factory() as session:
            return await _execute_query(session)

    except Exception as e:
        logger.error(f"Batch document query failed: {e}", exc_info=True)
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
    from kira.db.models import Document

    session = await _get_session(db)

    count_query = (
        select(func.count())
        .select_from(Document)
        .where(
            Document.user_id == user_id,
            Document.deleted_at.is_(None),
        )
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
    from kira.db.models import Document

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
    from kira.db.models import DocumentDeletionJob

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
    from kira.db.models import DocumentChunk

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
    from kira.db.models import DocumentChunk

    session = await _get_session(db)
    result = await session.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return list(result.scalars().all())


async def list_completed_chunks_for_user(
    user_id: UUID,
    db: AsyncSession | None = None,
) -> list[dict]:
    """Load persisted chunks for completed, non-deleted documents owned by a user."""
    from kira.constants import DocumentStatus
    from kira.db.models import Document, DocumentChunk
    from kira.db.session import async_session_factory

    async def _query(session: AsyncSession) -> list[dict]:
        result = await session.execute(
            select(DocumentChunk, Document.filename)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.user_id == user_id,
                Document.status == DocumentStatus.COMPLETED.value,
                Document.deleted_at.is_(None),
            )
            .order_by(Document.created_at.desc(), DocumentChunk.chunk_index)
        )

        chunks: list[dict] = []
        for chunk, filename in result.all():
            metadata = dict(chunk.meta_data or {})
            metadata.setdefault("document_id", str(chunk.document_id))
            metadata.setdefault("chunk_index", chunk.chunk_index)
            metadata.setdefault("filename", filename)
            if chunk.qdrant_point_id:
                metadata.setdefault("qdrant_point_id", chunk.qdrant_point_id)

            chunks.append(
                {
                    "index": chunk.chunk_index,
                    "content": chunk.content,
                    "token_count": chunk.token_count,
                    "metadata": metadata,
                }
            )

        return chunks

    if db is not None:
        return await _query(db)

    async with async_session_factory() as session:
        return await _query(session)


async def completed_chunks_signature_for_user(
    user_id: UUID,
    db: AsyncSession | None = None,
) -> tuple[int, int, str | None]:
    """Cheap fingerprint of the chunk set ``list_completed_chunks_for_user`` would return.

    Returns (completed documents, total chunks, latest document ``updated_at``). Documents are
    processed by the Celery worker in another process, so the API process compares this value
    with the one its in-memory BM25 index was built from to notice added/removed documents.
    """
    from kira.constants import DocumentStatus
    from kira.db.models import Document
    from kira.db.session import async_session_factory

    async def _query(session: AsyncSession) -> tuple[int, int, str | None]:
        result = await session.execute(
            select(
                func.count(Document.id),
                func.coalesce(func.sum(Document.chunk_count), 0),
                func.max(Document.updated_at),
            ).where(
                Document.user_id == user_id,
                Document.status == DocumentStatus.COMPLETED.value,
                Document.deleted_at.is_(None),
            )
        )
        doc_count, chunk_total, latest = result.one()
        return int(doc_count), int(chunk_total), latest.isoformat() if latest else None

    if db is not None:
        return await _query(db)

    async with async_session_factory() as session:
        return await _query(session)


class DocumentRepository:
    """Adapter that implements document persistence with SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with a request/session scoped DB session."""
        self.db = db

    async def create_document(
        self,
        user_id: UUID,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
    ) -> Any:
        """Create a document metadata record."""
        return await create_document(
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            storage_path=storage_path,
            db=self.db,
        )

    async def update_document_status(
        self,
        document_id: UUID,
        status: str,
        error_message: str | None = None,
        chunk_count: int = 0,
    ) -> Any | None:
        """Update document processing status."""
        return await update_document_status(
            document_id=document_id,
            status=status,
            error_message=error_message,
            chunk_count=chunk_count,
            db=self.db,
        )

    async def update_document_processing_task(
        self,
        document_id: UUID,
        task_id: str | None,
    ) -> Any | None:
        """Store or clear the Celery task ID for a document."""
        return await update_document_processing_task(
            document_id=document_id,
            task_id=task_id,
            db=self.db,
        )

    async def cancel_document(
        self,
        document_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ) -> Any | None:
        """Mark a document as cancelled."""
        return await cancel_document(
            document_id=document_id,
            user_id=user_id,
            reason=reason,
            db=self.db,
        )

    async def get_document(self, document_id: UUID, user_id: UUID | None = None) -> Any | None:
        """Fetch a document by ID, optionally scoped to a user."""
        return await get_document(
            document_id=document_id,
            user_id=user_id,
            db=self.db,
        )

    async def list_documents(
        self,
        user_id: UUID,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Any], int]:
        """List documents for a user."""
        return await list_documents(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset,
            db=self.db,
        )

    async def delete_document(self, document_id: UUID, user_id: UUID) -> bool:
        """Soft-delete a document."""
        return await delete_document(
            document_id=document_id,
            user_id=user_id,
            db=self.db,
        )

    async def create_deletion_retry_job(
        self,
        document_id: UUID,
        user_id: UUID,
        storage_path: str | None,
        cleanup_targets: list[str],
        last_error: str,
    ) -> Any:
        """Create a retry job for failed external document cleanup."""
        return await create_deletion_retry_job(
            document_id=document_id,
            user_id=user_id,
            storage_path=storage_path,
            cleanup_targets=cleanup_targets,
            last_error=last_error,
            db=self.db,
        )

    async def create_chunks(self, document_id: UUID, chunks: list[dict]) -> list[Any]:
        """Persist document chunks."""
        return await create_chunks(
            document_id=document_id,
            chunks=chunks,
            db=self.db,
        )

    async def get_document_chunks(self, document_id: UUID) -> list[Any]:
        """Fetch chunks for a document."""
        return await get_document_chunks(
            document_id=document_id,
            db=self.db,
        )
