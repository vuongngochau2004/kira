"""
RAG (Retrieval-Augmented Generation) domain service.

Encapsulates business logic for RAG query processing:
- Rejection detection to filter irrelevant citations
- Citation conversion from raw dicts to value objects
- Quality metrics aggregation

This service coordinates between infrastructure handlers and
domain rules without depending on specific LLM or retrieval implementations.
"""

from dataclasses import dataclass, field
from typing import Any

from src.shared.kernel.interfaces.handlers import Citation


# Vietnamese rejection patterns for detecting irrelevant document responses
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


@dataclass
class RAGResult:
    """Result of a RAG query processing step.

    Attributes:
        content: Generated text content
        citations: List of citations from retrieved documents
        metadata: Processing metadata (latency, docs retrieved, etc.)
        is_rejection: Whether the LLM determined no relevant docs exist
    """

    content: str = ""
    citations: list[Citation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    is_rejection: bool = False


class RAGService:
    """Domain service for RAG query processing rules.

    Encapsulates business logic that operates on RAG results:
    - Rejection detection from content analysis
    - Citation conversion and filtering
    - Relevance filtering based on LLM responses

    This service does NOT perform LLM calls or retrieval - those are
    infrastructure concerns handled by RAGHandler.
    """

    @staticmethod
    def is_rejection_response(content: str) -> bool:
        """Detect if LLM response indicates no relevant documents found.

        Checks for Vietnamese rejection patterns that indicate the LLM
        determined no relevant documents exist for the query.

        Args:
            content: LLM-generated response content

        Returns:
            True if response indicates rejection (no relevant docs)

        Example:
            >>> RAGService.is_rejection_response("Không tìm thấy tài liệu liên quan")
            True
            >>> RAGService.is_rejection_response("Dựa trên tài liệu, quy trình là...")
            False
        """
        content_lower = content.lower()
        return any(pattern in content_lower for pattern in REJECTION_PATTERNS)

    @staticmethod
    def convert_citations(raw_citations: list[dict]) -> list[Citation]:
        """Convert raw citation dicts to Citation value objects.

        Args:
            raw_citations: List of citation dicts with keys:
                filename, text, page, confidence, metadata

        Returns:
            List of Citation value objects
        """
        citations: list[Citation] = []
        for cite in raw_citations:
            if isinstance(cite, dict):
                citations.append(
                    Citation(
                        filename=cite.get("filename", ""),
                        text=cite.get("text", ""),
                        page=cite.get("page"),
                        confidence=cite.get("confidence", 1.0),
                        metadata=cite.get("metadata", {}),
                    )
                )
            elif isinstance(cite, Citation):
                citations.append(cite)
        return citations

    @staticmethod
    def filter_citations_by_relevance(
        citations: list[Citation],
        is_rejection: bool,
    ) -> list[Citation]:
        """Filter citations based on relevance detection.

        If LLM indicates no relevant documents, return empty list
        to avoid showing citations from irrelevant documents.

        Args:
            citations: Raw citations from retrieval
            is_rejection: Whether LLM indicated no relevant docs

        Returns:
            Filtered citations (empty if rejection detected)
        """
        if is_rejection:
            return []
        return citations

    @staticmethod
    def build_relevance_metadata(
        *,
        is_rejection: bool,
        rag_rejection: bool,
        content_rejection: bool,
        retrieved_count: int,
        returned_count: int,
        rejection_reason: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Build relevance filtering metadata for observability.

        Args:
            is_rejection: Combined rejection flag
            rag_rejection: Whether AgenticRAG detected rejection
            content_rejection: Whether content analysis detected rejection
            retrieved_count: Number of citations before filtering
            returned_count: Number of citations after filtering
            rejection_reason: Optional reason string
            error: Optional error message

        Returns:
            Metadata dict for HandlerResult
        """
        metadata: dict[str, Any] = {
            "relevance_filtering": {
                "enabled": True,
                "is_rejection": is_rejection,
                "rag_rejection": rag_rejection,
                "content_rejection": content_rejection,
                "retrieved_count": retrieved_count,
                "returned_count": returned_count,
                "filtered_count": retrieved_count - returned_count,
                "rejection_reason": rejection_reason
                or ("no_relevant_docs" if is_rejection else None),
            },
            "has_relevant_docs": not is_rejection,
        }
        if error:
            metadata["relevance_filtering"]["error"] = True
            metadata["relevance_filtering"]["error_message"] = error
        return metadata


__all__ = ["RAGService", "RAGResult", "REJECTION_PATTERNS"]