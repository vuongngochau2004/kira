"""Chat API endpoints - WebSocket and SSE streaming."""

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.shared.infrastructure.persistence.database.session import get_session
from src.shared.infrastructure.persistence.database.query import soft_delete_conversation
from src.modules.retrieval.infrastructure.document_store.document_repository import (
    create_conversation,
    get_conversation,
    list_conversations,
    create_message,
    get_conversation_messages,
)
from src.modules.chat.application.chat import ChatUseCase
from src.modules.chat.application.dto import ChatQuery
from src.modules.classification.domain import CompositeClassifier, KeywordStrategy, CachedStrategy, LLMStrategy
from src.modules.chat.infrastructure.handlers.rag_handler import RAGHandler
from src.modules.chat.infrastructure.handlers.conversational import ConversationalHandler
from src.shared.kernel.interfaces.classification import Intent
from src.shared.infrastructure.auth.dependencies import get_current_user
from src.shared.infrastructure.persistence.database.models import User
from src.models import ConversationCreate
from src.config.config import settings
from src.constants import (
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_CONVERSATION_LIMIT,
    DEFAULT_OFFSET,
    ERR_CONVERSATION_NOT_FOUND,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Global ChatUseCase instance (will be initialized on first use)
_chat_use_case = None


async def get_chat_use_case():
    """Get or create ChatUseCase instance with classifier and handlers from DI container."""
    global _chat_use_case
    if _chat_use_case is None:
        from src.shared.kernel.di import get_container
        from src.shared.kernel.interfaces.classification import ClassificationStrategyBase

        container = await get_container()
        classifier = await container.get(ClassificationStrategyBase)

        # Resolve handlers directly by their concrete types to bypass container's single-key limitation
        conversational_handler = await container.get(ConversationalHandler)
        rag_handler = await container.get(RAGHandler)

        handlers = {
            Intent.CONVERSATIONAL: conversational_handler,
            Intent.RAG: rag_handler,
        }

        _chat_use_case = ChatUseCase(
            classifier=classifier,
            handlers=handlers,
        )
    return _chat_use_case


# Request model for JSON body parsing
class ChatStreamRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    evaluate: bool = False
    evaluation_metrics: Optional[list[str]] = None


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


async def _load_conversation_history_if_exists(
    conversation_id: uuid.UUID | None,
    db: AsyncSession,
) -> list[dict]:
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
        messages = await get_conversation_messages(conversation_id, db=db)
        return [
            {
                "role": msg.role,
                "content": msg.content,
            }
            for msg in messages
        ]
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to load conversation history: {e}")
        return []


def _process_stream_routing_chunk(chunk_data: dict) -> tuple[str, str]:
    """Process routing chunk and update router name.

    Args:
        chunk_data: Routing chunk data dict

    Returns:
        Tuple of (formatted_router_name, sse_event)
    """
    router_name = chunk_data.get("router", "Agent")
    if chunk_data.get("intent"):
        router_name += f" ({chunk_data['intent']})"

    sse_event = f"data: {json.dumps({'type': 'routing', 'data': chunk_data})}\n\n"
    return router_name, sse_event


def _process_stream_retrieval_chunk(chunk_data: dict) -> tuple[dict, str]:
    """Process retrieval chunk and update retrieval stages.

    Args:
        chunk_data: Retrieval chunk data dict

    Returns:
        Tuple of (retrieval_stage_dict, sse_event)
    """
    retrieval_stage = {
        "iteration": chunk_data.get("iteration", 1),
        "strategy": chunk_data.get("strategy", "Hybrid"),
        "docs_retrieved": chunk_data.get("docs_retrieved", 0),
    }

    sse_event = f"data: {json.dumps({'type': 'retrieval', 'data': chunk_data})}\n\n"
    return retrieval_stage, sse_event


def _process_stream_content_chunk(chunk_data: dict) -> tuple[str, str]:
    """Process content chunk and extract text.

    Args:
        chunk_data: Content chunk data dict

    Returns:
        Tuple of (text_content, sse_event)
    """
    text = chunk_data.get("text", "")
    sse_event = f"data: {json.dumps({'type': 'content', 'data': {'text': text}})}\n\n"
    return text, sse_event


def _process_stream_thinking_chunk(chunk_data: dict) -> tuple[str, str]:
    """Process thinking chunk and extract reasoning text.

    Args:
        chunk_data: Thinking chunk data dict

    Returns:
        Tuple of (thinking_text, sse_event)
    """
    thinking_text = chunk_data.get("text", "")
    sse_event = f"data: {json.dumps({'type': 'thinking', 'data': {'text': thinking_text}})}\n\n"
    return thinking_text, sse_event


async def _ensure_conversation_exists(
    conversation_id: uuid.UUID | None,
    user_id: uuid.UUID,
    query: str,
    db: AsyncSession,
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
    )
    return conv.id


def _build_thinking_metadata(
    router_name: str | None,
    retrieval_stages: list[dict],
    thinking_content: list[str],
) -> dict | None:
    """Build thinking metadata from collected streaming data.

    Args:
        router_name: Name of router used
        retrieval_stages: List of retrieval stage dicts
        thinking_content: List of thinking text chunks

    Returns:
        Metadata dict or None if no metadata
    """
    thinking_metadata: dict = {}

    if router_name:
        thinking_metadata["router"] = router_name
    if retrieval_stages:
        thinking_metadata["retrieval"] = retrieval_stages
    if thinking_content:
        thinking_metadata["reasoning"] = "".join(thinking_content)

    return thinking_metadata if thinking_metadata else None


async def _save_streamed_messages(
    conversation_id: uuid.UUID | None,
    user_id: uuid.UUID,
    query: str,
    full_content: list[str],
    citations: list,
    thinking_metadata: dict | None,
    db: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Save user and assistant messages from streaming session.

    Args:
        conversation_id: Conversation UUID (may be None if new conversation)
        user_id: User ID (for ensuring conversation exists)
        query: Original user query
        full_content: List of content chunks
        citations: List of citation dicts
        thinking_metadata: Thinking metadata or None
        db: Database session

    Returns:
        Tuple of conversation UUID and created message UUID
    """
    # Ensure conversation exists
    conv_id = await _ensure_conversation_exists(
        conversation_id, user_id, query, db
    )

    # Save user message
    await create_message(
        conversation_id=conv_id,
        role="user",
        content=query,
        db=db,
    )

    # Save assistant message with thinking data
    msg = await create_message(
        conversation_id=conv_id,
        role="assistant",
        content="".join(full_content),
        sources=citations,
        thinking_data={"thinking": thinking_metadata} if thinking_metadata else None,
        db=db,
    )
    return conv_id, msg.id


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

    # Extract thinking metadata if available
    metadata = None
    if "metadata" in response and "thinking" in response["metadata"]:
        metadata = response["metadata"]

    msg = await create_message(
        conversation_id=conversation_id,
        role="assistant",
        content=response["content"],
        sources=response.get("sources", []),
        thinking_data=metadata,
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

    # Load conversation history if continuing conversation
    conversation_history = []
    if conv_id:
        messages = await get_conversation_messages(conv_id, db=db)
        conversation_history = [
            {
                "role": msg.role,
                "content": msg.content,
            }
            for msg in messages
        ]

    # Use ChatUseCase for intent-based routing
    chat_use_case = await get_chat_use_case()
    chat_query = ChatQuery(
        message=message,
        user_id=current_user.id,
        conversation_history=conversation_history,
    )
    result = await chat_use_case.execute(chat_query)

    await _save_messages(conv_id, message, result, db)

    # Return backward-compatible response structure
    return {
        "content": result.content,
        "citations": [{"filename": c.filename, "text": c.text, "page": c.page, "confidence": c.confidence} for c in result.citations] if result.citations else [],
        "conversation_id": str(conv_id),
        "message_id": str(uuid.uuid4()),
        "metadata": result.metadata,
    }


async def _stream_generator_v2(
    query: str,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    db: AsyncSession,
    evaluate: bool = False,
    evaluation_metrics: list[str] | None = None,
):
    """Generator for streaming response with real LLM streaming.

    Yields SSE events with chunk types:
    - routing: Router selection info
    - retrieval: RAG retrieval status
    - content: Text chunks from LLM
    - thinking: LLM reasoning chunks
    - metadata: Final metadata with citations
    - evaluation: RAGAS evaluation results (if enabled)
    - done: Completion signal
    """
    chat_use_case = await get_chat_use_case()

    # Collect full content for saving to DB
    full_content: list[str] = []
    citations: list = []
    conversation_id_to_save = conversation_id

    # Collect thinking data for metadata
    router_name: str | None = None
    retrieval_stages: list[dict] = []
    thinking_content: list[str] = []
    done_sent = False

    # Load conversation history if continuing conversation
    conversation_history = await _load_conversation_history_if_exists(
        conversation_id, db
    )

    try:
        chat_query = ChatQuery(
            message=query,
            user_id=user_id,
            conversation_id=conversation_id,
            conversation_history=conversation_history,
            context={"conversation_id": conversation_id} if conversation_id else None,
        )
        async for chunk in chat_use_case.execute_stream(chat_query):
            chunk_type = chunk.get("type")
            chunk_data = chunk.get("data", {})

            if chunk_type == "routing":
                router_name, sse_event = _process_stream_routing_chunk(chunk_data)
                yield sse_event

            elif chunk_type == "retrieval":
                retrieval_stage, sse_event = _process_stream_retrieval_chunk(chunk_data)
                retrieval_stages.append(retrieval_stage)
                yield sse_event

            elif chunk_type == "content":
                text, sse_event = _process_stream_content_chunk(chunk_data)
                full_content.append(text)
                yield sse_event

            elif chunk_type == "thinking":
                thinking_text, sse_event = _process_stream_thinking_chunk(chunk_data)
                thinking_content.append(thinking_text)
                yield sse_event

            elif chunk_type == "status":
                yield f"data: {json.dumps({'type': 'status', 'data': chunk_data})}\n\n"

            elif chunk_type == "metadata":
                # Collect citations from metadata
                if "citations" in chunk_data:
                    citations = chunk_data["citations"]
                elif "sources" in chunk_data:
                    citations = chunk_data["sources"]

                # Build thinking metadata
                thinking_metadata = _build_thinking_metadata(
                    router_name, retrieval_stages, thinking_content
                )

                # Save messages to DB
                saved_conversation_id, msg_id = await _save_streamed_messages(
                    conversation_id_to_save,
                    user_id,
                    query,
                    full_content,
                    citations,
                    thinking_metadata,
                    db,
                )

                # Emit final metadata
                yield f"data: {json.dumps({'type': 'metadata', 'data': {
                    **chunk_data,
                    'conversation_id': str(saved_conversation_id),
                    'message_id': str(msg_id),
                }})}\n\n"

                # RAGAS Evaluation (optional)
                if evaluate:
                    try:
                        yield f"data: {json.dumps({'type': 'evaluation_start', 'data': {}})}\n\n"

                        # Build contexts from citations
                        contexts = [c.get("content", "") for c in citations if c.get("content")]

                        if contexts:
                            from src.modules.evaluation.domain.service import get_evaluation_service
                            from src.models.evaluation import EvaluationRequest, EvaluationMetric

                            # Map metric names to enum
                            metrics = evaluation_metrics or ["faithfulness", "answer_relevancy"]
                            metric_enums = []
                            for m in metrics:
                                try:
                                    metric_enums.append(EvaluationMetric(m))
                                except ValueError:
                                    logger.warning(f"[RAGAS EVAL] Invalid metric: {m}")

                            if metric_enums:
                                eval_request = EvaluationRequest(
                                    query=query,
                                    answer="".join(full_content),
                                    contexts=contexts,
                                    metrics=metric_enums,
                                )

                                eval_service = get_evaluation_service()
                                eval_result = await eval_service.evaluate(eval_request)

                                yield f"data: {json.dumps({'type': 'evaluation', 'data': eval_result.model_dump()})}\n\n"
                            else:
                                yield f"data: {json.dumps({'type': 'evaluation_error', 'data': {'error': 'No valid metrics'}})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'evaluation_error', 'data': {'error': 'No contexts to evaluate'}})}\n\n"

                    except Exception as e:
                        logger.error(f"[RAGAS EVAL] Real-time evaluation failed: {e}")
                        yield f"data: {json.dumps({'type': 'evaluation_error', 'data': {'error': str(e)}})}\n\n"

                # Emit done signal
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                done_sent = True

            elif chunk_type == "done":
                if not done_sent:
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    done_sent = True

    except Exception as e:
        # Yield error
        yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}})}\n\n"
        if not done_sent:
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

    chat_use_case = await get_chat_use_case()
    chat_query = ChatQuery(message=query, user_id=user_id)
    result = await chat_use_case.execute(chat_query)

    content = result.content
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
        content=result.content,
        sources=[{"filename": c.filename, "text": c.text, "page": c.page} for c in result.citations] if result.citations else [],
        db=db,
    )

    yield f"data: {json.dumps({'done': True, 'message_id': str(msg.id), 'conversation_id': str(conversation_id)})}\n\n"


@router.post("/stream")
async def chat_stream(
    request: ChatStreamRequest,
    conversation_id: str | None = None,
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
        _stream_generator_v2(
            query=request.message,
            user_id=current_user.id,
            conversation_id=conv.id if conv else None,
            db=db,
            evaluate=request.evaluate,
            evaluation_metrics=request.evaluation_metrics,
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
                "thinking_data": msg.thinking_data or {},
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
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
