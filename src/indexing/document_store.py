"""Postgres document storage operations."""

import sys
from datetime import datetime, UTC
from uuid import UUID
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from src.database.models import Document, DocumentChunk, Conversation, Message
from src.database import get_session


async def _get_session(db: AsyncSession | None) -> AsyncSession:
    """Get database session, create new one if not provided."""
    if db is None:
        from src.database.session import async_session_factory
        return async_session_factory()
    return db


async def create_document(
    user_id: UUID,
    filename: str,
    file_type: str,
    file_size: int,
    storage_path: str,
    db: AsyncSession | None = None,
) -> Document:
    """Create a new document record."""
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
) -> Document | None:
    """Update document processing status."""
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
) -> Document | None:
    """Get a document by ID."""
    session = await _get_session(db)
    query = select(Document).where(
        Document.id == document_id,
        Document.deleted_at.is_(None),
    )

    if user_id is not None:
        query = query.where(Document.user_id == user_id)

    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list_documents(
    user_id: UUID,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession | None = None,
) -> tuple[list[Document], int]:
    """List user's documents."""
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
    """Soft delete a document."""
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


async def create_chunks(
    document_id: UUID,
    chunks: list[dict],
    db: AsyncSession | None = None,
) -> list[DocumentChunk]:
    """Create document chunks."""
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
) -> list[DocumentChunk]:
    """Get all chunks for a document."""
    session = await _get_session(db)
    result = await session.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return list(result.scalars().all())


async def create_conversation(
    user_id: UUID,
    title: str,
    db: AsyncSession | None = None,
) -> Conversation:
    """Create a new conversation."""
    session = await _get_session(db)
    conv = Conversation(
        user_id=user_id,
        title=title,
        message_count=0,
    )
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


async def create_message(
    conversation_id: UUID,
    role: str,
    content: str,
    sources: list | None = None,
    token_count: int | None = None,
    db: AsyncSession | None = None,
) -> Message:
    """Create a new message."""
    session = await _get_session(db)
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources or [],
        token_count=token_count,
    )
    session.add(msg)

    await session.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(
            message_count=Conversation.message_count + 1,
            last_message_at=datetime.utcnow(),
        )
    )

    await session.commit()
    await session.refresh(msg)
    return msg


async def get_conversation_messages(
    conversation_id: UUID,
    db: AsyncSession | None = None,
) -> list[Message]:
    """Get all messages in a conversation."""
    session = await _get_session(db)
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def list_conversations(
    user_id: UUID,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession | None = None,
) -> tuple[list[Conversation], int]:
    """List user's conversations."""
    session = await _get_session(db)

    count_query = select(func.count()).select_from(Conversation).where(
        Conversation.user_id == user_id,
        Conversation.deleted_at.is_(None),
    )

    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    result = await session.execute(
        select(Conversation)
        .where(
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
        )
        .order_by(
            Conversation.last_message_at.desc().nulls_last(),
            Conversation.created_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    conversations = result.scalars().all()
    return list(conversations), total


async def get_conversation(
    conversation_id: UUID,
    user_id: UUID,
    db: AsyncSession | None = None,
) -> Conversation | None:
    """Get a conversation by ID."""
    session = await _get_session(db)
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


__all__ = [
    "create_document",
    "update_document_status",
    "get_document",
    "list_documents",
    "delete_document",
    "create_chunks",
    "get_document_chunks",
    "create_conversation",
    "create_message",
    "get_conversation_messages",
    "list_conversations",
    "get_conversation",
]
