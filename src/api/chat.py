"""Chat API endpoints - WebSocket and SSE streaming."""

import sys
import uuid
import asyncio
import json
from pathlib import Path

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
from src.agents.orchestrator import create_orchestrator
from src.auth.dependencies import get_current_user
from src.database.models import User
from src.constants import (
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_CONVERSATION_LIMIT,
    DEFAULT_OFFSET,
    ERR_CONVERSATION_NOT_FOUND,
)

router = APIRouter()

# Global orchestrator instance (will be initialized on first use)
_orchestrator = None


def get_orchestrator():
    """Get or create orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = create_orchestrator()
    return _orchestrator


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


@router.post("/completions")
async def chat_completion(
    message: str,
    conversation_id: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,  # Currently unused, reserved for future
    max_tokens: int = DEFAULT_MAX_TOKENS,  # Currently unused, reserved for future
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Non-streaming chat completion."""
    conv_id = await _get_or_create_conversation_id(
        conversation_id, current_user.id, message, db
    )

    # Use orchestrator for multi-stage routing
    orchestrator = get_orchestrator()
    response = await orchestrator.query(
        user_query=message,
        user_id=current_user.id,
    )

    await _save_messages(conv_id, message, response, db)

    # Return backward-compatible response structure
    return {
        "content": response["content"],
        "citations": response.get("citations", []),
        "conversation_id": str(conv_id),
        "message_id": str(response.get("message_id", uuid.uuid4())),
        "metadata": response.get("metadata", {}),
    }


async def _stream_generator_v2(
    query: str,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    db: AsyncSession,
):
    """Generator for streaming response with real LLM streaming.

    Yields SSE events with chunk types:
    - routing: Router selection info
    - retrieval: RAG retrieval status
    - content: Text chunks from LLM
    - metadata: Final metadata with citations
    - done: Completion signal
    """
    orchestrator = get_orchestrator()

    # Collect full content for saving to DB
    full_content = []
    citations = []
    conversation_id_to_save = conversation_id

    try:
        async for chunk in orchestrator.query_stream(query, user_id):
            chunk_type = chunk.get("type")
            chunk_data = chunk.get("data", {})

            if chunk_type == "routing":
                # Emit routing info
                yield f"data: {json.dumps({'type': 'routing', 'data': chunk_data})}\n\n"

            elif chunk_type == "retrieval":
                # Emit retrieval status
                yield f"data: {json.dumps({'type': 'retrieval', 'data': chunk_data})}\n\n"

            elif chunk_type == "content":
                # Emit content chunk
                text = chunk_data.get("text", "")
                full_content.append(text)
                yield f"data: {json.dumps({'type': 'content', 'data': {'text': text}})}\n\n"

            elif chunk_type == "metadata":
                # Collect citations from metadata
                if "citations" in chunk_data:
                    citations = chunk_data["citations"]

                # Create conversation if needed
                if not conversation_id_to_save:
                    conv = await create_conversation(
                        user_id=user_id,
                        title=query[:100],
                        db=db,
                    )
                    conversation_id_to_save = conv.id

                # Save messages to DB
                await create_message(
                    conversation_id=conversation_id_to_save,
                    role="user",
                    content=query,
                    db=db,
                )

                msg = await create_message(
                    conversation_id=conversation_id_to_save,
                    role="assistant",
                    content="".join(full_content),
                    sources=citations,
                    db=db,
                )

                # Emit final metadata
                yield f"data: {json.dumps({'type': 'metadata', 'data': {
                    **chunk_data,
                    'conversation_id': str(conversation_id_to_save),
                    'message_id': str(msg.id),
                }})}\n\n"

                # Emit done signal
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        # Yield error
        yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def _stream_generator_legacy(
    query: str,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    history: list[dict],
    temperature: float,
    max_tokens: int,
    db: AsyncSession,
):
    """Legacy generator for backward compatibility (fake streaming)."""
    from src.constants import STREAM_CHUNK_SIZE

    orchestrator = get_orchestrator()
    response = await orchestrator.query(
        user_query=query,
        user_id=user_id,
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
    """Streaming chat completion with SSE.

    Uses real LLM streaming with structured chunk types:
    - routing: Router selection info
    - retrieval: RAG retrieval progress
    - content: Text chunks as they arrive
    - metadata: Final response metadata
    - done: Stream completion signal
    """
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

    return StreamingResponse(
        _stream_generator_v2(
            query=message,
            user_id=current_user.id,
            conversation_id=conv.id if conv else None,
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
