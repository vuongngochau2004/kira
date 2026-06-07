"""
RAG handler for document-based queries.

Handles RAG (Retrieval-Augmented Generation) queries with pre-classified intent.
"""

import time
from typing import Any, AsyncIterator
from uuid import UUID

from src.interfaces.classification import ClassificationResult, Intent
from src.interfaces.handlers import QueryHandlerBase, HandlerResult, HandlerConfig, Citation
from src.agents.rag_agent import AgenticRAG
from config.config import settings


class RAGHandler(QueryHandlerBase):
    """
    Handler for RAG (Retrieval-Augmented Generation) queries.

    Receives pre-classified RAG queries and executes retrieval + generation.
    No classification logic (SRP compliance).

    Example:
        >>> handler = RAGHandler()
        >>> result = await handler.handle("query", "user123", classification)
        >>> assert result.content
        >>> assert result.citations
    """

    def __init__(
        self,
        rag_agent: AgenticRAG | None = None,
        config: HandlerConfig | None = None
    ):
        """
        Initialize RAG handler.

        Args:
            rag_agent: Optional pre-configured RAG agent
            config: Optional handler configuration
        """
        self.rag_agent = rag_agent
        self.config = config or HandlerConfig(max_retrieved_docs=settings.retrieval_k)

    def can_handle(self, classification: ClassificationResult) -> bool:
        """
        Check if handler can handle the classification.

        Args:
            classification: Pre-classified intent and metadata

        Returns:
            True if intent is RAG
        """
        return classification.intent == Intent.RAG

    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None
    ) -> HandlerResult:
        """
        Execute RAG query (non-streaming).

        Args:
            query: User query string
            user_id: User ID for personalization
            classification: Pre-classified intent (must be RAG)
            context: Additional context (conversation history, etc.)

        Returns:
            HandlerResult with content, citations, and metadata

        Raises:
            ValueError: If classification intent is not RAG
        """
        if classification.intent != Intent.RAG:
            raise ValueError(f"RAGHandler cannot handle intent: {classification.intent}")

        t0 = time.perf_counter()
        conversation_history = context.get("conversation_history") if context else None

        # Initialize RAG agent if not provided
        if self.rag_agent is None:
            self.rag_agent = AgenticRAG(
                max_iterations=3,
                retrieval_k=self.config.max_retrieved_docs,
            )

        try:
            result = await self.rag_agent.query(
                query,
                user_id,
                conversation_history=conversation_history
            )

            # Convert citations
            citations = self._convert_citations(result.get("citations", []))

            return HandlerResult(
                content=result.get("content", ""),
                citations=citations,
                metadata={
                    "handler": self.get_name(),
                    "docs_retrieved": result.get("total_docs", 0),
                    "latency_ms": (time.perf_counter() - t0) * 1000,
                    "classification": classification.to_dict(),
                    "retrieval_history": result.get("retrieval_history", []),
                }
            )

        except Exception as e:
            return HandlerResult(
                content="Có lỗi xảy ra khi xử lý câu hỏi.",
                citations=[],
                metadata={
                    "handler": self.get_name(),
                    "error": str(e),
                    "latency_ms": (time.perf_counter() - t0) * 1000,
                },
                status="error",
                error=str(e)
            )

    async def handle_stream(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None
    ) -> AsyncIterator[dict]:
        """
        Execute RAG query with streaming response.

        Args:
            query: User query string
            user_id: User ID for personalization
            classification: Pre-classified intent (must be RAG)
            context: Additional context

        Yields:
            Dict chunks with type: "retrieval", "content", "metadata", "done"
        """
        if classification.intent != Intent.RAG:
            yield {
                "type": "metadata",
                "data": {
                    "status": "error",
                    "error": f"RAGHandler cannot handle intent: {classification.intent}",
                    "handler": self.get_name(),
                }
            }
            return

        t0 = time.perf_counter()
        conversation_history = context.get("conversation_history") if context else None

        # Initialize RAG agent if not provided
        if self.rag_agent is None:
            self.rag_agent = AgenticRAG(
                max_iterations=3,
                retrieval_k=self.config.max_retrieved_docs,
            )

        try:
            async for chunk in self.rag_agent.query_stream(
                query,
                user_id,
                conversation_history=conversation_history
            ):
                yield chunk

        except Exception as e:
            yield {
                "type": "metadata",
                "data": {
                    "status": "error",
                    "error": str(e),
                    "handler": self.get_name(),
                    "latency_ms": (time.perf_counter() - t0) * 1000,
                }
            }

    def get_config(self) -> HandlerConfig:
        """Get handler configuration."""
        return self.config

    def get_name(self) -> str:
        """Get handler name."""
        return "RAGHandler"

    def _convert_citations(self, raw_citations: list[dict]) -> list[Citation]:
        """
        Convert raw citation dicts to Citation objects.

        Args:
            raw_citations: List of citation dicts

        Returns:
            List of Citation objects
        """
        citations = []

        for cite in raw_citations:
            if isinstance(cite, dict):
                citations.append(Citation(
                    filename=cite.get("filename", ""),
                    text=cite.get("text", ""),
                    page=cite.get("page"),
                    confidence=cite.get("confidence", 1.0),
                    metadata=cite.get("metadata", {})
                ))
            elif isinstance(cite, Citation):
                citations.append(cite)

        return citations
