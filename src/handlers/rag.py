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

    Features relevance-aware citation filtering to avoid showing citations
    from documents that LLM has deemed irrelevant to the query.

    Example:
        >>> handler = RAGHandler()
        >>> result = await handler.handle("query", "user123", classification)
        >>> assert result.content
        >>> # Citations only returned if LLM found relevant docs
        >>> if result.metadata.get("has_relevant_docs"):
        ...     assert result.citations
    """

    # Rejection patterns to detect LLM responses indicating no relevant documents found
    REJECTION_PATTERNS = [
        "không tìm thấy",
        "không có thông tin",
        "tài liệu không đề cập",
        "văn bản không quy định",
        "không đề cập đến",
        "không có quy định",
        "dữ liệu không có",
        "không tài liệu nào",
    ]

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

    def _is_rejection_response(self, content: str) -> bool:
        """
        Detect if LLM response indicates no relevant documents were found.

        This prevents showing citations from documents that the LLM has deemed
        irrelevant to the user's query.

        Args:
            content: LLM-generated response content

        Returns:
            True if response indicates rejection (no relevant docs), False otherwise

        Example:
            >>> handler._is_rejection_response("Không tìm thấy tài liệu liên quan")
            True
            >>> handler._is_rejection_response("Dựa trên tài liệu, quy trình là...")
            False
        """
        content_lower = content.lower()
        return any(pattern in content_lower for pattern in self.REJECTION_PATTERNS)

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

            content = result.get("content", "")

            # ✅ Relevance detection: Check BOTH AgenticRAG metadata AND content analysis
            # Priority: Use rejection_detected from AgenticRAG if available, fallback to content analysis
            rag_rejection = result.get("rejection_detected", False)
            content_rejection = self._is_rejection_response(content)
            is_rejection = rag_rejection or content_rejection

            # Convert citations (AgenticRAG should already return empty if rejection)
            raw_citations = result.get("citations", [])
            citations = self._convert_citations(raw_citations)

            # ✅ Conditional citation return: Only return citations if LLM found relevant docs
            # If LLM says "no relevant docs", don't show citations from irrelevant documents
            final_citations = [] if is_rejection else citations

            return HandlerResult(
                content=content,
                citations=final_citations,
                metadata={
                    "handler": self.get_name(),
                    "docs_retrieved": result.get("total_docs", 0),
                    "latency_ms": (time.perf_counter() - t0) * 1000,
                    "classification": classification.to_dict(),
                    "retrieval_history": result.get("retrieval_history", []),
                    # Observability: Track filtering decisions from BOTH layers
                    "relevance_filtering": {
                        "enabled": True,
                        "is_rejection": is_rejection,
                        "rag_rejection": rag_rejection,
                        "content_rejection": content_rejection,
                        "retrieved_count": len(raw_citations),
                        "returned_count": len(final_citations),
                        "filtered_count": len(raw_citations) - len(final_citations),
                        "rejection_reason": result.get("rejection_reason") or ("no_relevant_docs" if is_rejection else None),
                    },
                    "has_relevant_docs": not is_rejection,
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
                    "relevance_filtering": {
                        "enabled": True,
                        "error": True,
                        "error_message": str(e),
                    },
                    "has_relevant_docs": False,
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

        Note:
            Citations are filtered based on LLM relevance detection.
            If LLM indicates no relevant documents, citation chunks are not yielded.
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
            # Track streaming chunks for relevance filtering
            content_chunks = []
            citation_chunks = []
            has_rejection = False

            async for chunk in self.rag_agent.query_stream(
                query,
                user_id,
                conversation_history=conversation_history
            ):
                # Collect content chunks for relevance detection, but also yield immediately
                if chunk.get("type") == "content":
                    content_chunks.append(chunk)
                    yield chunk  # ✅ Yield content immediately for real-time streaming
                # Collect citation chunks for potential filtering
                elif chunk.get("type") == "metadata" and "citations" in chunk.get("data", {}):
                    citation_chunks.append(chunk)
                else:
                    # Pass through other chunks (retrieval, done, etc.)
                    yield chunk

            # ✅ After streaming, check relevance and decide on citations
            full_content = "".join([
                c.get("data", {}).get("text", "")
                for c in content_chunks
            ])

            # Check rejection from BOTH content analysis and AgenticRAG metadata (if available)
            content_rejection = self._is_rejection_response(full_content)

            # Try to get rejection metadata from citation chunks (AgenticRAG might have sent it)
            rag_rejection = False
            for chunk in citation_chunks:
                if chunk.get("type") == "metadata" and chunk.get("data", {}).get("rejection_detected"):
                    rag_rejection = True
                    break

            has_rejection = rag_rejection or content_rejection

            # Only yield citation chunks if LLM found relevant documents
            if not has_rejection:
                for citation_chunk in citation_chunks:
                    # Add observability to citation metadata
                    if "data" in citation_chunk and isinstance(citation_chunk["data"], dict):
                        citation_chunk["data"]["relevance_filtered"] = False
                    yield citation_chunk
            else:
                # Log filtering decision with detailed observability
                yield {
                    "type": "metadata",
                    "data": {
                        "relevance_filtering": {
                            "enabled": True,
                            "is_rejection": True,
                            "rag_rejection": rag_rejection,
                            "content_rejection": content_rejection,
                            "filtered_citation_count": len(citation_chunks),
                            "rejection_reason": "no_relevant_docs",
                        }
                    },
                }

        except Exception as e:
            yield {
                "type": "metadata",
                "data": {
                    "status": "error",
                    "error": str(e),
                    "handler": self.get_name(),
                    "latency_ms": (time.perf_counter() - t0) * 1000,
                    "relevance_filtering": {
                        "enabled": True,
                        "error": True,
                        "error_message": str(e),
                    },
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
