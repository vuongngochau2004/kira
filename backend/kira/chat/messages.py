"""Conversation and message persistence for chat requests (load history, save turns)."""

import logging
import re
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from kira.chat.citations import EnrichCitations
from kira.chat.history import bound_history
from kira.chat.repository import (
    create_conversation,
    create_message,
    get_conversation,
    get_recent_owned_messages,
)
from kira.constants import (
    ERR_CONVERSATION_NOT_FOUND,
)
from kira.retrieval.search import PostgresRetrievalDocumentAdapter

logger = logging.getLogger(__name__)

# Handler metadata keys that are stored with the assistant message.
PERSISTED_METADATA_KEYS = (
    "attachments",
    "drafting",
    "document_type",
    "documents_used",
    "legal",
)


def citation_contexts(citations: list[dict]) -> list[str]:
    """Evaluation contexts from citations; handlers put the excerpt in `content` or `text`."""
    contexts: list[str] = []
    for citation in citations:
        value = citation.get("content") or citation.get("text")
        if value:
            contexts.append(str(value))
    return contexts


async def get_or_create_conversation_id(
    conversation_id: str | None,
    user_id: uuid.UUID,
    first_message: str,
    db: AsyncSession,
) -> uuid.UUID:
    """Get existing conversation or create new one."""
    if conversation_id:
        conv = await get_conversation(
            conversation_id=uuid.UUID(conversation_id),
            user_id=user_id,
            db=db,
        )
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERR_CONVERSATION_NOT_FOUND,
            )
        return conv.id

    conv = await create_conversation(
        user_id=user_id,
        title=first_message[:100],
        db=db,
    )
    return conv.id


async def load_conversation_history(
    conversation_id: uuid.UUID | None,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> list[dict[str, str]]:
    """Load conversation history for context if conversation exists.

    Args:
        conversation_id: UUID of conversation or None
        db: Database session

    Returns:
        List of message dicts with role and content
    """
    if not conversation_id:
        return []

    try:
        messages = await get_recent_owned_messages(conversation_id, user_id, db=db)
        return bound_history(
            [
                {
                    "role": msg.role,
                    "content": msg.content,
                }
                for msg in messages
            ]
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to load conversation history: {e}")
        return []


async def ensure_conversation_exists(
    conversation_id: uuid.UUID | None,
    user_id: uuid.UUID,
    query: str,
    db: AsyncSession,
    *,
    commit: bool = True,
) -> uuid.UUID:
    """Ensure conversation exists, create if needed.

    Args:
        conversation_id: Existing conversation UUID or None
        user_id: User ID
        query: Query string for title
        db: Database session

    Returns:
        Conversation UUID (existing or newly created)
    """
    if conversation_id:
        return conversation_id

    conv = await create_conversation(
        user_id=user_id,
        title=query[:100],
        db=db,
        commit=commit,
    )
    return conv.id


def build_message_metadata(
    router_name: str | None,
    retrieval_stages: list[dict],
) -> dict | None:
    """Build message metadata from collected streaming data.

    Args:
        router_name: Name of router used
        retrieval_stages: List of retrieval stage dicts

    Returns:
        Metadata dict or None if no metadata
    """
    metadata: dict = {}

    if router_name:
        metadata["router"] = router_name
    if retrieval_stages:
        metadata["retrieval"] = retrieval_stages

    return metadata if metadata else None


async def resolve_citation_filenames(citations: list[dict], db: AsyncSession) -> list[dict]:
    """Look up filenames in database for all citations and fill them in."""
    if not citations:
        return citations

    doc_ids: list[str] = [
        c.get("document_id") or (c.get("metadata") or {}).get("document_id")
        for c in citations
        if c.get("document_id") or (c.get("metadata") or {}).get("document_id")
    ]
    if not doc_ids:
        return citations

    try:
        return await EnrichCitations(documents=PostgresRetrievalDocumentAdapter()).execute(
            citations
        )
    except Exception as e:
        logger.warning(f"Failed to resolve citation filenames: {e}")

    return citations


async def save_streamed_messages(
    conversation_id: uuid.UUID | None,
    user_id: uuid.UUID,
    query: str,
    full_content: list[str],
    citations: list,
    metadata: dict | None,
    db: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Save user and assistant messages from streaming session.

    Args:
        conversation_id: Conversation UUID (may be None if new conversation)
        user_id: User ID (for ensuring conversation exists)
        query: Original user query
        full_content: List of content chunks
        citations: List of citation dicts
        metadata: Message metadata or None
        db: Database session

    Returns:
        Tuple of conversation UUID and created message UUID
    """
    # Ensure conversation exists
    conv_id = await ensure_conversation_exists(conversation_id, user_id, query, db, commit=False)

    # Save user message
    await create_message(
        conversation_id=conv_id,
        role="user",
        content=query,
        db=db,
        commit=False,
    )

    is_rejection = metadata.get("rejection_detected", False) if metadata else False
    if is_rejection:
        content_str = clean_rejection_content("".join(full_content))
    else:
        content_str = "".join(full_content)
    resolved_citations = await resolve_citation_filenames(citations, db)

    # Save assistant message with metadata
    msg = await create_message(
        conversation_id=conv_id,
        role="assistant",
        content=content_str,
        sources=resolved_citations,
        metadata=metadata,
        db=db,
        commit=False,
    )
    await db.commit()
    return conv_id, msg.id


async def save_messages(
    conversation_id: uuid.UUID,
    user_message: str,
    response,
    db: AsyncSession,
) -> uuid.UUID:
    """Save user and assistant messages."""
    await create_message(
        conversation_id=conversation_id,
        role="user",
        content=user_message,
        db=db,
    )

    # Extract metadata if available. ChatUseCase returns a ChatResult dataclass,
    # while older callers may still pass dict-like responses.
    if isinstance(response, dict):
        metadata = response.get("metadata") or {}
        response_content = response.get("content", "")
        citations = response.get("citations") or response.get("sources") or []
    else:
        metadata = getattr(response, "metadata", {}) or {}
        response_content = getattr(response, "content", "")
        citations = getattr(response, "citations", []) or []

    db_metadata = {}
    router_name = metadata.get("handler")
    if router_name:
        db_metadata["router"] = router_name

    for key in PERSISTED_METADATA_KEYS:
        if key in metadata:
            db_metadata[key] = metadata[key]

    is_rejection = False
    if metadata.get("rejection_detected"):
        db_metadata["rejection_detected"] = True
        db_metadata["rejection_reasoning"] = clean_rejection_content(
            metadata.get("rejection_reasoning") or ""
        )
        is_rejection = True
    elif metadata.get("relevance_filtering", {}).get("is_rejection"):
        db_metadata["rejection_detected"] = True
        db_metadata["rejection_reasoning"] = clean_rejection_content(response_content)
        is_rejection = True

    content_str = clean_rejection_content(response_content) if is_rejection else response_content
    citations = [c.to_dict() if hasattr(c, "to_dict") else c for c in citations]
    resolved_citations = await resolve_citation_filenames(citations, db)

    msg = await create_message(
        conversation_id=conversation_id,
        role="assistant",
        content=content_str,
        sources=resolved_citations,
        metadata=db_metadata if db_metadata else None,
        db=db,
    )
    return msg.id


def clean_rejection_content(content: str) -> str:
    """Strip raw document bracket citations (e.g. [Document 1]) from rejection messages."""
    if not content:
        return ""
    # Remove ([Document X], [Document Y]...)
    cleaned = re.sub(
        r"\s*\(\s*\[Document\s+\d+\][\s\d\w,\[\]-]*\)",
        "",
        content,
        flags=re.IGNORECASE,
    )
    # Remove [Document X] without parentheses
    cleaned = re.sub(
        r"\s*\[Document\s+\d+\]",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()
