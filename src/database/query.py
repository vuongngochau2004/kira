"""Common query patterns to avoid N+1 issues."""

import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.database.models import User, Document, DocumentChunk, Conversation, Message


async def get_user_by_email(email: str, include_deleted: bool = False) -> Optional[User]:
    """Get user by email (with or without soft delete filter)."""
    query = select(User).where(User.email == email)
    if not include_deleted:
        query = query.where(User.deleted_at.is_(None))
    return await query


async def get_document_with_chunks(
    doc_id: uuid.UUID,
    db_session,
    include_deleted: bool = False,
) -> Optional[Document]:
    """Get document with chunks eagerly loaded (avoids N+1)."""
    query = (
        select(Document)
        .options(selectinload(Document.chunks))
        .where(Document.id == doc_id)
    )
    if not include_deleted:
        query = query.where(Document.deleted_at.is_(None))
    result = await db_session.execute(query)
    return result.scalar_one_or_none()


async def get_conversation_with_messages(
    conv_id: uuid.UUID,
    db_session,
    include_deleted: bool = False,
) -> Optional[Conversation]:
    """Get conversation with messages eagerly loaded (avoids N+1)."""
    query = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conv_id)
    )
    if not include_deleted:
        query = query.where(Conversation.deleted_at.is_(None))
    result = await db_session.execute(query)
    return result.scalar_one_or_none()


async def list_user_documents(
    user_id: uuid.UUID,
    db_session,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Document], int]:
    """List user documents with total count (optimized with single query)."""
    # Get documents with count in same query
    count_query = (
        select(func.count())
        .select_from(Document)
        .where(Document.user_id == user_id)
        .where(Document.deleted_at.is_(None))
    )
    total_result = await db_session.execute(count_query)
    total = total_result.scalar_one()

    # Get paginated documents
    query = (
        select(Document)
        .where(Document.user_id == user_id)
        .where(Document.deleted_at.is_(None))
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db_session.execute(query)
    documents = result.scalars().all()

    return list(documents), total


async def list_user_conversations(
    user_id: uuid.UUID,
    db_session,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Conversation], int]:
    """List user conversations with total count."""
    # Get count
    count_query = (
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.user_id == user_id)
        .where(Conversation.deleted_at.is_(None))
    )
    total_result = await db_session.execute(count_query)
    total = total_result.scalar_one()

    # Get conversations ordered by last_message_at
    query = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .where(Conversation.deleted_at.is_(None))
        .order_by(
            Conversation.last_message_at.desc().nulls_last(),
            Conversation.created_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    result = await db_session.execute(query)
    conversations = result.scalars().all()

    return list(conversations), total


async def get_chunks_by_document(document_id: uuid.UUID, db_session) -> list[DocumentChunk]:
    """Get all chunks for a document in order."""
    query = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    result = await db_session.execute(query)
    return list(result.scalars().all())


async def soft_delete_document(doc_id: uuid.UUID, db_session) -> bool:
    """Soft delete a document (sets deleted_at)."""
    query = (
        select(Document)
        .where(Document.id == doc_id)
        .where(Document.deleted_at.is_(None))
    )
    result = await db_session.execute(query)
    doc = result.scalar_one_or_none()
    if doc:
        from datetime import datetime
        doc.deleted_at = datetime.utcnow()
        await db_session.commit()
        return True
    return False


async def soft_delete_conversation(conv_id: uuid.UUID, db_session) -> bool:
    """Soft delete a conversation (sets deleted_at)."""
    query = (
        select(Conversation)
        .where(Conversation.id == conv_id)
        .where(Conversation.deleted_at.is_(None))
    )
    result = await db_session.execute(query)
    conv = result.scalar_one_or_none()
    if conv:
        from datetime import datetime
        conv.deleted_at = datetime.utcnow()
        await db_session.commit()
        return True
    return False
