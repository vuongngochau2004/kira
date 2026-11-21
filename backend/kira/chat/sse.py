"""Chat SSE contract: turns handler chunks into the Server-Sent Events the frontend parses."""

import asyncio
import json
import logging
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from kira.chat.dto import ChatQuery
from kira.chat.messages import (
    PERSISTED_METADATA_KEYS,
    build_message_metadata,
    citation_contexts,
    clean_rejection_content,
    load_conversation_history,
    resolve_citation_filenames,
    save_streamed_messages,
)
from kira.deps import get_chat_use_case

logger = logging.getLogger(__name__)

MAX_STREAM_TEXT_PART_CHARS = 48


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


def _merge_routing_step(pipeline_steps: list[dict], chunk_data: dict) -> None:
    """Record intent classification as the first pipeline-trace step.

    Both the chat graph and the selected handler emit a routing chunk, so later chunks update
    the existing ``classify`` step instead of adding a duplicate.
    """
    routing = {
        key: chunk_data[key]
        for key in ("router", "intent", "confidence")
        if chunk_data.get(key) is not None
    }
    if pipeline_steps and pipeline_steps[0].get("stage") == "classify":
        pipeline_steps[0]["metadata"].update(routing)
    else:
        pipeline_steps.insert(0, {"stage": "classify", "metadata": routing})


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


async def stream_chat_events(
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
    - evaluation: DeepEval evaluation results (if enabled)
    - done: Completion signal
    """
    chat_use_case = get_chat_use_case()

    # Collect full content for saving to DB
    full_content: list[str] = []
    provisional_seen = False
    preview_pending = False
    final_replacement_seen = False
    metadata_sent = False
    error_sent = False
    citations: list = []
    conversation_id_to_save = conversation_id

    # Collect data for metadata
    router_name: str | None = None
    retrieval_stages: list[dict] = []
    # Ordered pipeline trace (classification + each graph node) persisted for the chat UI.
    pipeline_steps: list[dict] = []
    done_sent = False
    stream = None

    # Load conversation history if continuing conversation
    conversation_history = await load_conversation_history(conversation_id, user_id, db)

    try:
        chat_query = ChatQuery(
            message=query,
            user_id=user_id,
            conversation_id=conversation_id,
            conversation_history=conversation_history,
            context={"conversation_id": conversation_id} if conversation_id else None,
        )
        stream = chat_use_case.execute_stream(chat_query)
        async for chunk in stream:
            chunk_type = chunk.get("type")
            chunk_data = chunk.get("data", {})

            if chunk_type == "routing":
                router_name, sse_event = _process_stream_routing_chunk(chunk_data)
                _merge_routing_step(pipeline_steps, chunk_data)
                yield sse_event

            elif chunk_type == "retrieval":
                retrieval_stage, sse_event = _process_stream_retrieval_chunk(chunk_data)
                retrieval_stages.append(retrieval_stage)
                yield sse_event

            elif chunk_type == "content":
                text, _ = _process_stream_content_chunk(chunk_data)
                is_provisional = chunk_data.get("provisional") is True
                if is_provisional:
                    provisional_seen = True
                    preview_pending = True
                else:
                    full_content.append(text)
                for text_part in _split_stream_text(text):
                    if is_provisional:
                        payload = {**chunk_data, "text": text_part}
                        yield f"data: {json.dumps({'type': 'content', 'data': payload})}\n\n"
                    else:
                        yield _content_sse_event(text_part)
                    await asyncio.sleep(0)

            elif chunk_type == "content_replace":
                text = chunk_data.get("text")
                if not isinstance(text, str):
                    raise ValueError("Invalid content replacement")
                if chunk_data.get("provisional") is False:
                    full_content = [text]
                    final_replacement_seen = True
                    preview_pending = False
                else:
                    provisional_seen = True
                    full_content = []
                    preview_pending = bool(text)
                yield f"data: {json.dumps({'type': 'content_replace', 'data': chunk_data})}\n\n"

            elif chunk_type == "status":
                pipeline_steps.append(
                    {"stage": chunk_data.get("stage"), "metadata": chunk_data.get("metadata") or {}}
                )
                yield f"data: {json.dumps({'type': 'status', 'data': chunk_data})}\n\n"

            elif chunk_type == "metadata":
                if metadata_sent:
                    continue
                if provisional_seen and not final_replacement_seen:
                    raise ValueError("RAG metadata arrived before final replacement")
                # Collect citations from metadata
                if "citations" in chunk_data:
                    citations = chunk_data["citations"]
                elif "sources" in chunk_data:
                    citations = chunk_data["sources"]

                citations = await resolve_citation_filenames(citations, db)
                chunk_data["citations"] = citations
                chunk_data["sources"] = citations

                # Build message metadata
                metadata = build_message_metadata(router_name, retrieval_stages)
                if metadata is None:
                    metadata = {}
                if len(pipeline_steps) > 1:  # classification alone is not worth a timeline
                    metadata["pipeline"] = pipeline_steps
                for key in PERSISTED_METADATA_KEYS:
                    if key in chunk_data:
                        metadata[key] = chunk_data[key]
                if chunk_data.get("rejection_detected"):
                    metadata["rejection_detected"] = True
                    cleaned_reasoning = clean_rejection_content(
                        chunk_data.get("rejection_reasoning") or ""
                    )
                    metadata["rejection_reasoning"] = cleaned_reasoning
                    chunk_data["rejection_reasoning"] = cleaned_reasoning
                    # Clear citations when response is rejected (not grounded in retrieved docs)
                    citations = []
                    chunk_data["citations"] = []
                    chunk_data["sources"] = []

                # Save messages to DB
                saved_conversation_id, msg_id = await save_streamed_messages(
                    conversation_id_to_save,
                    user_id,
                    query,
                    full_content,
                    citations,
                    metadata,
                    db,
                )
                metadata_sent = True

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

                # DeepEval evaluation (optional)
                if evaluate:
                    try:
                        yield f"data: {json.dumps({'type': 'evaluation_start', 'data': {}})}\n\n"

                        # Build contexts from citations
                        contexts = citation_contexts(citations)

                        if contexts:
                            from kira.evaluation.schemas import (
                                EvaluationMetric,
                                EvaluationRequest,
                            )
                            from kira.evaluation.service import get_evaluation_service

                            # Map metric names to enum
                            metrics = evaluation_metrics or ["faithfulness", "answer_relevancy"]
                            metric_enums = []
                            for m in metrics:
                                try:
                                    metric_enums.append(EvaluationMetric(m))
                                except ValueError:
                                    logger.warning(f"[DEEPEVAL] Invalid metric: {m}")

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
                        logger.error(f"[DEEPEVAL] Real-time evaluation failed: {e}")
                        yield f"data: {json.dumps({'type': 'evaluation_error', 'data': {'error': str(e)}})}\n\n"

                # Emit done signal
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                done_sent = True

            elif chunk_type == "done":
                if not done_sent:
                    if provisional_seen and not final_replacement_seen and not error_sent:
                        yield f"data: {json.dumps({'type': 'content_replace', 'data': {'text': '', 'provisional': True}})}\n\n"
                        yield f"data: {json.dumps({'type': 'error', 'data': {'error': 'Chat stream failed'}})}\n\n"
                        error_sent = True
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    done_sent = True

            elif chunk_type == "error":
                if preview_pending:
                    yield f"data: {json.dumps({'type': 'content_replace', 'data': {'text': '', 'provisional': True}})}\n\n"
                    preview_pending = False
                if not error_sent:
                    yield f"data: {json.dumps({'type': 'error', 'data': {'error': 'Chat stream failed'}})}\n\n"
                    error_sent = True

    except asyncio.CancelledError:
        logger.info("Chat stream cancelled for user_id=%s", user_id)
        raise
    except Exception:
        logger.exception("Chat stream failed for user_id=%s", user_id)
        if preview_pending:
            yield f"data: {json.dumps({'type': 'content_replace', 'data': {'text': '', 'provisional': True}})}\n\n"
        if not error_sent:
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': 'Chat stream failed'}})}\n\n"
        if not done_sent:
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
    finally:
        if stream is not None:
            await stream.aclose()
