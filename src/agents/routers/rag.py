"""RAG router for document-based queries."""

from uuid import UUID
from typing import Any, AsyncIterator

from src.agents.rag_agent import AgenticRAG
from src.agents.routers.base import BaseRouter
from config.config import settings


class RAGRouter(BaseRouter):
    """Router for RAG (Retrieval-Augmented Generation) queries.

    Handles any query that requires knowledge from documents in the database.
    """

    def __init__(self, rag_agent: AgenticRAG | None = None):
        """Initialize RAG router.

        Args:
            rag_agent: Optional pre-configured RAG agent
        """
        self.rag_agent = rag_agent

    async def can_handle(self, query: str) -> float:
        """Check if query is suitable for RAG with confidence scoring.

        Since RAG is the default for most non-conversational queries,
        this returns medium confidence for substantive queries.

        Args:
            query: User query

        Returns:
            Confidence score 0.0-1.0
        """
        query_lower = query.lower()

        # Check for file/document related terms
        file_indicators = ["file", "tài liệu", "tập tin", "doc", "docx", "pdf", "trích dẫn"]
        if any(term in query_lower for term in file_indicators):
            return 0.95

        # Check for document-related terms (boosts confidence)
        doc_indicators = [
            "tìm", "kiểm tra", "tra cứu", "theo", "trong", "về", "liên quan",
            "quy định", "thủ tục", "cách", "như thế nào", "làm sao"
        ]

        indicator_matches = sum(
            1 for term in doc_indicators
            if term in query_lower
        )

        # Medium-high confidence for queries with doc indicators
        if indicator_matches >= 1:
            return 0.7

        # Medium confidence for longer queries (likely research-oriented)
        word_count = len(query.split())
        if word_count >= 4:
            return 0.5

        # Low confidence for very short queries (likely conversational)
        return 0.2

    async def handle(self, query: str, user_id: str | UUID) -> dict[str, Any]:
        """Process query with RAG (non-streaming).

        Args:
            query: User query
            user_id: User ID for filtering

        Returns:
            Response dict with RAG-generated answer
        """
        # Initialize RAG agent if not provided
        if self.rag_agent is None:
            self.rag_agent = AgenticRAG(
                max_iterations=3,
                retrieval_k=settings.retrieval_k,
            )

        try:
            result = await self.rag_agent.query(query, user_id)

            # Add backward-compatible fields
            result.setdefault("citations", [])
            result.setdefault("sources", [])
            result.setdefault("metadata", {
                "router": self.get_name(),
                "agent": "rag",
                "chunks_found": result.get("total_docs", 0),
            })

            return result

        except Exception as e:
            return {
                "content": "Có lỗi xảy ra khi xử lý câu hỏi.",
                "status": "error",
                "error": str(e),
                "citations": [],
                "sources": [],
                "metadata": {"router": self.get_name(), "agent": "rag"},
                "latency_ms": 0,
                "retrieval_history": [],
            }

    async def handle_stream(
        self,
        query: str,
        user_id: str | UUID,
    ) -> AsyncIterator[dict]:
        """Process query with RAG streaming.

        Args:
            query: User query
            user_id: User ID for filtering

        Yields:
            Dict chunks with type:
            - "retrieval": {iteration, strategy, docs_retrieved, new_docs, sufficient}
            - "content": {text}
            - "metadata": {total_docs, iterations, status, citations}
        """
        # Initialize RAG agent if not provided
        if self.rag_agent is None:
            self.rag_agent = AgenticRAG(
                max_iterations=3,
                retrieval_k=settings.retrieval_k,
            )

        try:
            async for chunk in self.rag_agent.query_stream(query, user_id):
                yield chunk

        except Exception as e:
            # Yield error as metadata
            yield {
                "type": "metadata",
                "data": {
                    "status": "error",
                    "error": str(e),
                    "router": self.get_name(),
                    "agent": "rag",
                },
            }


__all__ = ["RAGRouter"]
