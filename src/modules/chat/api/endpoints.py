"""Chat API endpoints - WebSocket and SSE streaming."""

import asyncio
import json
import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.persistence.database.session import get_session
from src.shared.infrastructure.persistence.database.query import soft_delete_conversation
from src.modules.chat.composition import (
    create_conversation,
    create_message,
    get_chat_use_case,
    get_conversation,
    get_conversation_messages,
    list_conversations,
)
from src.modules.chat.application.dto import ChatQuery
from src.shared.infrastructure.auth.dependencies import get_current_user
from src.shared.infrastructure.persistence.database.models import User
from src.modules.chat.api.requests import ChatStreamRequest, ConversationCreate
from src.constants import (
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_CONVERSATION_LIMIT,
    DEFAULT_OFFSET,
    ERR_CONVERSATION_NOT_FOUND,
)

router = APIRouter()
logger = logging.getLogger(__name__)
MAX_STREAM_TEXT_PART_CHARS = 48
PERSISTED_METADATA_KEYS = (
    "attachments",
    "drafting",
    "document_type",
    "documents_used",
)


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


def _split_stream_text(text: str) -> list[str]:
    """Split large provider chunks into smaller readable SSE content events."""
    if not text or len(text) <= MAX_STREAM_TEXT_PART_CHARS:
        return [text] if text else []

    parts = re.findall(r"\S+\s*|\s+", text)
    if not parts:
        return [text]

    result: list[str] = []
    buffer = ""
    for part in parts:
        if buffer and len(buffer) + len(part) > MAX_STREAM_TEXT_PART_CHARS:
            result.append(buffer)
            buffer = part
        else:
            buffer += part
    if buffer:
        result.append(buffer)

    return result


def _content_sse_event(text: str) -> str:
    return f"data: {json.dumps({'type': 'content', 'data': {'text': text}})}\n\n"


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


def _build_message_metadata(
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


async def _resolve_citation_filenames(citations: list[dict], db: AsyncSession) -> list[dict]:
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
        from src.modules.retrieval.infrastructure.document_store import get_documents_batch

        doc_mapping = await get_documents_batch(doc_ids, db=db)

        for c in citations:
            doc_id = c.get("document_id") or (c.get("metadata") or {}).get("document_id")
            if doc_id and str(doc_id) in doc_mapping:
                filename = doc_mapping[str(doc_id)]
                c["filename"] = filename
                c["source"] = filename
                c["title"] = filename
    except Exception as e:
        logger.warning(f"Failed to resolve citation filenames: {e}")

    return citations


def _clean_rejection_content(content: str) -> str:
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


async def _save_streamed_messages(
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
    conv_id = await _ensure_conversation_exists(conversation_id, user_id, query, db)

    # Save user message
    await create_message(
        conversation_id=conv_id,
        role="user",
        content=query,
        db=db,
    )

    is_rejection = metadata.get("rejection_detected", False) if metadata else False
    if is_rejection:
        content_str = _clean_rejection_content("".join(full_content))
    else:
        content_str = "".join(full_content)
    resolved_citations = await _resolve_citation_filenames(citations, db)

    # Save assistant message with metadata
    msg = await create_message(
        conversation_id=conv_id,
        role="assistant",
        content=content_str,
        sources=resolved_citations,
        metadata=metadata,
        db=db,
    )
    return conv_id, msg.id


async def _save_messages(
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
        db_metadata["rejection_reasoning"] = _clean_rejection_content(
            metadata.get("rejection_reasoning") or ""
        )
        is_rejection = True
    elif metadata.get("relevance_filtering", {}).get("is_rejection"):
        db_metadata["rejection_detected"] = True
        db_metadata["rejection_reasoning"] = _clean_rejection_content(response_content)
        is_rejection = True

    if is_rejection:
        content_str = _clean_rejection_content(response_content)
    else:
        content_str = response_content
    citations = [c.to_dict() if hasattr(c, "to_dict") else c for c in citations]
    resolved_citations = await _resolve_citation_filenames(citations, db)

    msg = await create_message(
        conversation_id=conversation_id,
        role="assistant",
        content=content_str,
        sources=resolved_citations,
        metadata=db_metadata if db_metadata else None,
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
    conv_id = await _get_or_create_conversation_id(conversation_id, current_user.id, message, db)

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

    msg_id = await _save_messages(conv_id, message, result, db)

    # Return backward-compatible response structure
    raw_citations = (
        [
            {
                "filename": c.filename,
                "text": c.text,
                "page": c.page,
                "confidence": c.confidence,
                "document_id": (
                    str(getattr(c, "document_id"))
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
    resolved_citations = await _resolve_citation_filenames(raw_citations, db)

    is_rejection = result.metadata.get("rejection_detected", False) if result.metadata else False
    content_str = _clean_rejection_content(result.content) if is_rejection else result.content
    return {
        "content": content_str,
        "citations": resolved_citations,
        "conversation_id": str(conv_id),
        "message_id": str(msg_id),
        "metadata": result.metadata,
    }


async def _stream_generator(
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

    # Collect data for metadata
    router_name: str | None = None
    retrieval_stages: list[dict] = []
    done_sent = False

    # Load conversation history if continuing conversation
    conversation_history = await _load_conversation_history_if_exists(conversation_id, db)

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
                text, _ = _process_stream_content_chunk(chunk_data)
                full_content.append(text)
                for text_part in _split_stream_text(text):
                    yield _content_sse_event(text_part)
                    await asyncio.sleep(0)

            elif chunk_type == "status":
                yield f"data: {json.dumps({'type': 'status', 'data': chunk_data})}\n\n"

            elif chunk_type == "metadata":
                # Collect citations from metadata
                if "citations" in chunk_data:
                    citations = chunk_data["citations"]
                elif "sources" in chunk_data:
                    citations = chunk_data["sources"]

                citations = await _resolve_citation_filenames(citations, db)
                chunk_data["citations"] = citations
                chunk_data["sources"] = citations

                # Build message metadata
                metadata = _build_message_metadata(router_name, retrieval_stages)
                if metadata is None:
                    metadata = {}
                for key in PERSISTED_METADATA_KEYS:
                    if key in chunk_data:
                        metadata[key] = chunk_data[key]
                if chunk_data.get("rejection_detected"):
                    metadata["rejection_detected"] = True
                    cleaned_reasoning = _clean_rejection_content(
                        chunk_data.get("rejection_reasoning") or ""
                    )
                    metadata["rejection_reasoning"] = cleaned_reasoning
                    chunk_data["rejection_reasoning"] = cleaned_reasoning
                    # Clear citations when response is rejected (not grounded in retrieved docs)
                    citations = []
                    chunk_data["citations"] = []
                    chunk_data["sources"] = []

                # Save messages to DB
                saved_conversation_id, msg_id = await _save_streamed_messages(
                    conversation_id_to_save,
                    user_id,
                    query,
                    full_content,
                    citations,
                    metadata,
                    db,
                )

                # Emit final metadata
                yield f"data: {
                    json.dumps(
                        {
                            'type': 'metadata',
                            'data': {
                                **chunk_data,
                                'conversation_id': str(saved_conversation_id),
                                'message_id': str(msg_id),
                            },
                        }
                    )
                }\n\n"

                # RAGAS Evaluation (optional)
                if evaluate:
                    try:
                        yield f"data: {json.dumps({'type': 'evaluation_start', 'data': {}})}\n\n"

                        # Build contexts from citations
                        contexts = [c.get("content", "") for c in citations if c.get("content")]

                        if contexts:
                            from src.modules.evaluation.domain.service import get_evaluation_service
                            from src.modules.evaluation.api.schemas import (
                                EvaluationRequest,
                                EvaluationMetric,
                            )

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
        _stream_generator(
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
            sources = await _resolve_citation_filenames(sources, db)
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
