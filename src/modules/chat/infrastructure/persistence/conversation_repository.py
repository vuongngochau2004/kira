"""SQLAlchemy persistence operations for chat conversations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession


async def create_conversation(
    user_id: UUID,
    title: str,
    db: AsyncSession,
) -> Any:
    """Create a new conversation."""
    from src.shared.infrastructure.persistence.database.models import Conversation

    conv = Conversation(
        user_id=user_id,
        title=title,
        message_count=0,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def create_message(
    conversation_id: UUID,
    role: str,
    content: str,
    db: AsyncSession,
    sources: list | None = None,
    token_count: int | None = None,
    metadata: dict | None = None,
) -> Any:
    """Create a message and update conversation counters."""
    from src.shared.infrastructure.persistence.database.models import Conversation, Message

    validated_metadata = {}
    if metadata and isinstance(metadata, dict):
        allowed_keys = {
            "steps",
            "iterations",
            "router",
            "agent",
            "latency_ms",
            "retrieval",
            "rejection_detected",
            "rejection_reasoning",
            "attachments",
            "drafting",
            "document_type",
            "documents_used",
        }
        validated_metadata = {
            key: value
            for key, value in metadata.items()
            if key in allowed_keys and isinstance(value, (str, int, float, list, dict, bool))
        }

    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources or [],
        token_count=token_count,
        meta_data=validated_metadata,
    )
    db.add(msg)

    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(
            message_count=Conversation.message_count + 1,
            last_message_at=datetime.utcnow(),
        )
    )
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_conversation_messages(
    conversation_id: UUID,
    db: AsyncSession,
) -> list[Any]:
    """Get all messages in a conversation."""
    from src.shared.infrastructure.persistence.database.models import Message

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def list_conversations(
    user_id: UUID,
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Any], int]:
    """List conversations owned by a user."""
    from src.shared.infrastructure.persistence.database.models import Conversation

    count_query = select(func.count()).select_from(Conversation).where(
        Conversation.user_id == user_id,
        Conversation.deleted_at.is_(None),
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    result = await db.execute(
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
    return list(result.scalars().all()), total


async def get_conversation(
    conversation_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> Any | None:
    """Get a user-owned conversation by ID."""
    from src.shared.infrastructure.persistence.database.models import Conversation

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


__all__ = [
    "create_conversation",
    "create_message",
    "get_conversation",
    "get_conversation_messages",
    "list_conversations",
]
