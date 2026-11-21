"""Application DTOs exposed by the RAG bounded context."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RAGCitation:
    """Citation returned by the RAG use case, independent of transport."""

    filename: str
    text: str
    page: int | None = None
    confidence: float = 1.0
    document_id: str | None = None
    chunk_index: int | None = None


@dataclass(frozen=True)
class RAGExecutionResult:
    """Final, transport-agnostic result of an agentic RAG execution."""

    content: str
    citations: list[RAGCitation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    rejected: bool = False


__all__ = ["RAGCitation", "RAGExecutionResult"]
