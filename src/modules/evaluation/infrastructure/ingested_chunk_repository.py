"""Persistence adapter for evaluation-corpus sampling."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.shared.infrastructure.persistence.database.models import Document, DocumentChunk


class SqlAlchemyIngestedChunkRepository:
    """Read completed, user-owned chunks for evaluation dataset generation."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def list_completed_chunks(self, user_id: UUID) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Document, DocumentChunk)
                .join(DocumentChunk, DocumentChunk.document_id == Document.id)
                .where(Document.user_id == user_id)
                .where(Document.deleted_at.is_(None))
                .where(Document.status == "completed")
                .order_by(Document.created_at.desc(), Document.filename, DocumentChunk.chunk_index)
            )
            return [
                {
                    "document_id": str(document.id),
                    "filename": document.filename,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content or "",
                    "metadata": chunk.meta_data or {},
                }
                for document, chunk in result.all()
            ]


__all__ = ["SqlAlchemyIngestedChunkRepository"]
