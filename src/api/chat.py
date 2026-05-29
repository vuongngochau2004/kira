"""Chat API endpoints - WebSocket and SSE streaming."""

import sys
import uuid
import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.database import get_session
from src.indexing.document_store import (
    create_conversation,
    get_conversation,
    list_conversations,
    create_message,
    get_conversation_messages,
)
from src.agents.rag_agent import generate_response
from src.auth.dependencies import get_current_user
from src.database.models import User
from src.constants import (
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_CONVERSATION_LIMIT,
    DEFAULT_OFFSET,
    ERR_CONVERSATION_NOT_FOUND,
    STREAM_CHUNK_SIZE,
)

router = APIRouter()


@router.post("/completions")
async def chat_completion(
    message: str,
    conversation_id: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Non-streaming chat completion."""
    conv_id = await _get_or_create_conversation_id(
        conversation_id, current_user.id, message, db
    )

    history = await _get_conversation_history(conv_id, db)
    response = await generate_response(
        query=message,
        user_id=current_user.id,
        conversation_history=history,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    await _save_messages(conv_id, message, response, db)

    return {
        "content": response["content"],
        "citations": response.get("citations", []),
        "conversation_id": str(conv_id),
        "message_id": str(response.get("message_id", "")),
        "metadata": response.get("metadata", {}),
    }


async def _get_or_create_conversation_id(
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


async def _get_conversation_history(
    conversation_id: uuid.UUID,
    db: AsyncSession,
) -> list[dict]:
    """Get conversation history for context."""
    messages = await get_conversation_messages(conversation_id, db=db)
    return [{"role": msg.role, "content": msg.content} for msg in messages]


async def _save_messages(
    conversation_id: uuid.UUID,
    user_message: str,
    response: dict,
    db: AsyncSession,
) -> uuid.UUID:
    """Save user and assistant messages."""
    await create_message(
        conversation_id=conversation_id,
        role="user",
        content=user_message,
        db=db,
    )

    msg = await create_message(
        conversation_id=conversation_id,
        role="assistant",
        content=response["content"],
        sources=response.get("sources", []),
        db=db,
    )
    return msg.id


async def _stream_generator(
    query: str,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    history: list[dict],
    temperature: float,
    max_tokens: int,
    db: AsyncSession,
):
    """Generator for streaming response."""
    response = await generate_response(
        query=query,
        user_id=user_id,
        conversation_history=history,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    content = response["content"]
    for i in range(0, len(content), STREAM_CHUNK_SIZE):
        chunk = content[i:i + STREAM_CHUNK_SIZE]
        yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
        await asyncio.sleep(0.01)

    if not conversation_id:
        conv = await create_conversation(
            user_id=user_id,
            title=query[:100],
            db=db,
        )
        conversation_id = conv.id

    await create_message(
        conversation_id=conversation_id,
        role="user",
        content=query,
        db=db,
    )

    msg = await create_message(
        conversation_id=conversation_id,
        role="assistant",
        content=response["content"],
        sources=response.get("sources", []),
        db=db,
    )

    yield f"data: {json.dumps({'done': True, 'message_id': str(msg.id), 'conversation_id': str(conversation_id)})}\n\n"


@router.post("/stream")
async def chat_stream(
    message: str,
    conversation_id: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Streaming chat completion with SSE."""
    conv = None
    if conversation_id:
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

    history = await _get_conversation_history(conv.id, db) if conv else []

    return StreamingResponse(
        _stream_generator(
            query=message,
            user_id=current_user.id,
            conversation_id=conv.id if conv else None,
            history=history,
            temperature=temperature,
            max_tokens=max_tokens,
            db=db,
        ),
        media_type="text/event-stream",
    )


@router.get("/conversations")
async def get_conversations_list(
    limit: int = DEFAULT_CONVERSATION_LIMIT,
    offset: int = DEFAULT_OFFSET,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List user's conversations."""
    conversations, total = await list_conversations(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        db=db,
    )

    return {
        "conversations": [
            {
                "id": str(conv.id),
                "title": conv.title,
                "message_count": conv.message_count,
                "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
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
    title: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Create a new conversation."""
    conv = await create_conversation(
        user_id=current_user.id,
        title=title,
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

    return {
        "id": str(conv.id),
        "title": conv.title,
        "message_count": conv.message_count,
        "messages": [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "sources": msg.sources,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
    }
