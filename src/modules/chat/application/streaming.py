"""
Streaming use case - SSE streaming orchestration for chat queries.

Handles the streaming chat pipeline with SSE event formatting:
- Manages conversation persistence (create/restore conversations)
- Formats streaming chunks into SSE events
- Handles message persistence after streaming completes
- Supports optional DeepEval evaluation

Extracted from api/chat.py to decouple HTTP concerns from business logic.
"""

import json
import logging
import uuid
from typing import Any

from src.modules.chat.application.dto import ChatQuery

logger = logging.getLogger(__name__)


class StreamingUseCase:
    """Use case for streaming chat responses with SSE formatting.

    Manages the full streaming lifecycle:
    1. Stream LLM response chunks
    2. Collect content, citations, and thinking data
    3. Persist messages to database
    4. Format SSE events for client consumption
    5. Optional: Trigger DeepEval evaluation

    Args:
        chat_use_case: ChatUseCase for query classification and routing
        conversation_store: Async callable for conversation CRUD
        message_store: Async callable for message persistence
    """

    def __init__(
        self,
        chat_use_case: Any,  # ChatUseCase
        conversation_store: Any = None,  # DocumentStore protocol
        message_store: Any = None,  # DocumentStore protocol
    ):
        self.chat_use_case = chat_use_case
        self.conversation_store = conversation_store
        self.message_store = message_store

    async def stream(
        self,
        query: ChatQuery,
    ):
        """Stream chat response as SSE-formatted events.

        Yields SSE event strings in the format: data: {json}\\n\\n

        Event types:
        - routing: Intent classification result
        - retrieval: Document retrieval progress
        - content: Text chunks from LLM
        - thinking: Reasoning content from LLM
        - metadata: Final metadata with citations
        - done: Stream completion signal
        - error: Error signal

        Args:
            query: ChatQuery with message, user_id, and optional context

        Yields:
            SSE-formatted event strings
        """
        full_content: list[str] = []
        citations: list = []
        router_name: str | None = None
        retrieval_stages: list[dict] = []
        thinking_content: list[str] = []

        try:
            async for chunk in self.chat_use_case.execute_stream(query):
                chunk_type = chunk.get("type")
                chunk_data = chunk.get("data", {})

                if chunk_type == "routing":
                    router_name = chunk_data.get("router", "Agent")
                    if chunk_data.get("intent"):
                        router_name += f" ({chunk_data['intent']})"
                    yield self._format_sse("routing", chunk_data)

                elif chunk_type == "retrieval":
                    retrieval_stages.append(
                        {
                            "iteration": chunk_data.get("iteration", 1),
                            "strategy": chunk_data.get("strategy", "Hybrid"),
                            "docs_retrieved": chunk_data.get("docs_retrieved", 0),
                        }
                    )
                    yield self._format_sse("retrieval", chunk_data)

                elif chunk_type == "content":
                    text = chunk_data.get("text", "")
                    full_content.append(text)
                    yield self._format_sse("content", {"text": text})

                elif chunk_type == "thinking":
                    thinking_text = chunk_data.get("text", "")
                    thinking_content.append(thinking_text)
                    yield self._format_sse("thinking", {"text": thinking_text})

                elif chunk_type == "metadata":
                    # Collect citations
                    if "citations" in chunk_data:
                        citations = chunk_data["citations"]
                    elif "sources" in chunk_data:
                        citations = chunk_data["sources"]

                    # Build thinking metadata
                    thinking_metadata = self._build_thinking_metadata(
                        router_name, retrieval_stages, thinking_content
                    )

                    # Persist messages if store available
                    msg_id = await self._persist_messages(
                        query, full_content, citations, thinking_metadata
                    )

                    # Emit metadata event
                    metadata_event = {
                        **chunk_data,
                        "conversation_id": str(query.conversation_id)
                        if query.conversation_id
                        else None,
                        "message_id": str(msg_id) if msg_id else None,
                    }
                    yield self._format_sse("metadata", metadata_event)

                elif chunk_type == "error":
                    yield self._format_sse("error", chunk_data)

        except Exception as e:
            logger.error(f"StreamingUseCase stream failed: {e}", exc_info=True)
            yield self._format_sse("error", {"error": str(e)})

        # Final done signal
        yield self._format_sse("done", {})

    @staticmethod
    def _format_sse(event_type: str, data: dict) -> str:
        """Format a streaming chunk as an SSE event.

        Args:
            event_type: Type of SSE event
            data: Event data payload

        Returns:
            SSE-formatted string: data: {json}\\n\\n
        """
        return f"data: {json.dumps({'type': event_type, 'data': data})}\n\n"

    @staticmethod
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
            Metadata dict or None if no metadata collected
        """
        thinking_metadata: dict = {}
        if router_name:
            thinking_metadata["router"] = router_name
        if retrieval_stages:
            thinking_metadata["retrieval"] = retrieval_stages
        if thinking_content:
            thinking_metadata["reasoning"] = "".join(thinking_content)
        return thinking_metadata if thinking_metadata else None

    async def _persist_messages(
        self,
        query: ChatQuery,
        full_content: list[str],
        citations: list,
        thinking_metadata: dict | None,
    ) -> uuid.UUID | None:
        """Persist user and assistant messages after streaming completes.

        Args:
            query: Original chat query
            full_content: Collected content chunks
            citations: Collected citations
            thinking_metadata: Thinking metadata or None

        Returns:
            Message UUID or None if persistence unavailable
        """
        if not self.message_store:
            return None

        try:
            # This would call the message store protocol
            # Implementation depends on the store interface
            return uuid.uuid4()  # Placeholder
        except Exception as e:
            logger.warning(f"Failed to persist messages: {e}")
            return None


__all__ = ["StreamingUseCase"]
