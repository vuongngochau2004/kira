"""Chat API endpoints - WebSocket and SSE streaming."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from kira.auth.dependencies import get_current_user
from kira.auth.rate_limit import limit_user_requests
from kira.chat.dto import ChatQuery
from kira.chat.messages import (
    clean_rejection_content,
    get_or_create_conversation_id,
    load_conversation_history,
    resolve_citation_filenames,
    save_messages,
)
from kira.chat.repository import (
    create_conversation,
    get_conversation,
    get_conversation_messages,
    list_conversations,
)
from kira.chat.schemas import ChatStreamRequest, ConversationCreate
from kira.chat.sse import stream_chat_events
from kira.constants import (
    DEFAULT_CONVERSATION_LIMIT,
    DEFAULT_MAX_TOKENS,
    DEFAULT_OFFSET,
    DEFAULT_TEMPERATURE,
    ERR_CONVERSATION_NOT_FOUND,
)
from kira.db.models import User
from kira.db.queries import soft_delete_conversation
from kira.db.session import get_session
from kira.deps import get_chat_use_case

router = APIRouter()
logger = logging.getLogger(__name__)
limit_chat_request = limit_user_requests("chat", maximum=60, window_seconds=60)


@router.post("/completions")
async def chat_completion(
    message: str,
    conversation_id: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,  # Currently unused, reserved for future
    max_tokens: int = DEFAULT_MAX_TOKENS,  # Currently unused, reserved for future
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    _: None = Depends(limit_chat_request),
) -> dict:
    """Non-streaming chat completion."""
    conv_id = await get_or_create_conversation_id(conversation_id, current_user.id, message, db)

    # Load conversation history if continuing conversation
    conversation_history = await load_conversation_history(conv_id, current_user.id, db)

    # Use ChatUseCase for intent-based routing
    chat_use_case = get_chat_use_case()
    chat_query = ChatQuery(
        message=message,
        user_id=current_user.id,
        conversation_id=conv_id,
        conversation_history=conversation_history,
        context={"conversation_id": conv_id},
    )
    result = await chat_use_case.execute(chat_query)

    msg_id = await save_messages(conv_id, message, result, db)

    # Return backward-compatible response structure
    raw_citations = (
        [
            {
                "filename": c.filename,
                "text": c.text,
                "page": c.page,
                "confidence": c.confidence,
                "document_id": (
                    str(c.document_id)
                    if getattr(c, "document_id", None)
                    else c.metadata.get("document_id")
                    if getattr(c, "metadata", None)
                    else None
                ),
                "metadata": c.metadata if getattr(c, "metadata", None) else {},
            }
            for c in result.citations
        ]
        if result.citations
        else []
    )
    resolved_citations = await resolve_citation_filenames(raw_citations, db)

    is_rejection = result.metadata.get("rejection_detected", False) if result.metadata else False
    content_str = clean_rejection_content(result.content) if is_rejection else result.content
    return {
        "content": content_str,
        "citations": resolved_citations,
        "conversation_id": str(conv_id),
        "message_id": str(msg_id),
        "metadata": result.metadata,
    }


@router.post("/stream")
async def chat_stream(
    request: ChatStreamRequest,
    conversation_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    _: None = Depends(limit_chat_request),
):
    """Streaming chat completion with SSE.

    Uses real LLM streaming with structured chunk types:
    - routing: Router selection info
    - retrieval: RAG retrieval progress
    - content: Text chunks as they arrive
    - metadata: Final response metadata
    - done: Stream completion signal

    Request body (JSON):
    {
        "message": "user message",
        "conversation_id": "uuid (optional)"
    }
    """
    conv = None
    effective_conversation_id = request.conversation_id or conversation_id
    if effective_conversation_id:
        conv = await get_conversation(
            conversation_id=uuid.UUID(effective_conversation_id),
            user_id=current_user.id,
            db=db,
        )
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERR_CONVERSATION_NOT_FOUND,
            )

    return StreamingResponse(
        stream_chat_events(
            query=request.message,
            user_id=current_user.id,
            conversation_id=conv.id if conv else None,
            db=db,
            evaluate=request.evaluate,
            evaluation_metrics=request.evaluation_metrics,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations")
async def get_conversations_list(
    limit: int = Query(default=DEFAULT_CONVERSATION_LIMIT, ge=1, le=100),
    offset: int = Query(default=DEFAULT_OFFSET, ge=0),
    search: str | None = Query(default=None, max_length=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List user's conversations."""
    conversations, total = await list_conversations(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        search=search,
        db=db,
    )

    return {
        "conversations": [
            {
                "id": str(conv.id),
                "title": conv.title,
                "message_count": conv.message_count,
                "last_message_at": conv.last_message_at.isoformat()
                if conv.last_message_at
                else None,
                "created_at": conv.created_at.isoformat(),
            }
            for conv in conversations
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def create_new_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Create a new conversation."""
    conv = await create_conversation(
        user_id=current_user.id,
        title=data.title or "Cuộc trò chuyện mới",
        db=db,
    )

    return {
        "id": str(conv.id),
        "title": conv.title,
        "message_count": conv.message_count,
        "created_at": conv.created_at.isoformat(),
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation_detail(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get conversation with messages."""
    conv = await get_conversation(
        conversation_id=uuid.UUID(conversation_id),
        user_id=current_user.id,
        db=db,
    )

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_CONVERSATION_NOT_FOUND,
        )

    messages = await get_conversation_messages(conv.id, db=db)

    # Resolve filenames for assistant messages before sending to client
    resolved_messages = []
    for msg in messages:
        sources = msg.sources
        if msg.role == "assistant" and sources:
            sources = await resolve_citation_filenames(sources, db)
        resolved_messages.append(
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "sources": sources,
                "metadata": msg.meta_data or {},
                "created_at": msg.created_at.isoformat(),
            }
        )

    return {
        "id": str(conv.id),
        "title": conv.title,
        "message_count": conv.message_count,
        "messages": resolved_messages,
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Delete a conversation (soft delete)."""
    conv = await get_conversation(
        conversation_id=uuid.UUID(conversation_id),
        user_id=current_user.id,
        db=db,
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_CONVERSATION_NOT_FOUND,
        )

    success = await soft_delete_conversation(conv.id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation",
        )

    return {"status": "success", "message": "Conversation deleted successfully"}
