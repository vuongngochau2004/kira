"""Application contracts for RAG workflow execution."""

from collections.abc import AsyncIterator
from typing import Any, Protocol
from uuid import UUID

from src.shared.ports.llm import LLMPort


class RAGWorkflowPort(Protocol):
    """Workflow engine contract consumed by the RAG application service.

    LangGraph is an infrastructure implementation detail.  The application
    service depends only on this contract so a different workflow engine can
    be introduced without changing callers or use cases.
    """

    llm: LLMPort | None

    async def run(
        self,
        query: str,
        user_id: str,
        conversation_id: UUID | None = None,
    ) -> dict[str, Any]: ...

    def run_stream(
        self,
        query: str,
        user_id: str,
        conversation_id: UUID | None = None,
    ) -> AsyncIterator[dict[str, Any]]: ...


__all__ = ["RAGWorkflowPort"]
