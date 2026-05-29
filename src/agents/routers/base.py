"""Base router interface for query routing."""

from abc import ABC, abstractmethod
from uuid import UUID
from typing import Any, AsyncIterator


class BaseRouter(ABC):
    """Base class for all query routers."""

    @abstractmethod
    async def can_handle(self, query: str) -> float:
        """Check if this router can handle the query.

        Args:
            query: User query string

        Returns:
            Confidence score between 0.0 and 1.0
            - 0.0: Cannot handle at all
            - 0.5-0.7: Maybe can handle
            - 0.8+: Confidently can handle
        """
        pass

    @abstractmethod
    async def handle(self, query: str, user_id: str | UUID) -> dict[str, Any]:
        """Process the query and generate response.

        Args:
            query: User query string
            user_id: User ID for personalization/filtering

        Returns:
            Response dict with:
                - content: str (answer)
                - status: str (success, conversational, error)
                - citations: list (optional, for backward compatibility)
                - sources: list (optional, for backward compatibility)
                - metadata: dict (optional, for backward compatibility)
                - latency_ms: float (processing time)
                - retrieval_history: list (for RAG queries)
        """
        pass

    async def handle_stream(
        self,
        query: str,
        user_id: str | UUID,
    ) -> AsyncIterator[dict]:
        """Process the query with streaming response.

        Default implementation falls back to non-streaming handle()
        and yields the complete response as a single chunk.

        Args:
            query: User query string
            user_id: User ID for personalization/filtering

        Yields:
            Dict chunks with type:
            - "content": {text: str}
            - "metadata": {status, citations, sources, etc.}
        """
        # Default fallback: non-streaming
        result = await self.handle(query, user_id)

        # Yield content
        content = result.get("content", "")
        if content:
            yield {"type": "content", "data": {"text": content}}

        # Yield metadata
        metadata = {
            "status": result.get("status", "success"),
            "router": self.get_name(),
        }
        if "citations" in result:
            metadata["citations"] = result["citations"]
        if "sources" in result:
            metadata["sources"] = result["sources"]
        if "latency_ms" in result:
            metadata["latency_ms"] = result["latency_ms"]
        if "retrieval_history" in result:
            metadata["retrieval_history"] = result["retrieval_history"]
        if "total_docs" in result:
            metadata["total_docs"] = result["total_docs"]

        yield {"type": "metadata", "data": metadata}

    def get_name(self) -> str:
        """Get router name for logging."""
        return self.__class__.__name__


__all__ = ["BaseRouter"]
