"""Orchestrator agent for multi-stage query routing."""

import time
from typing import Any, AsyncIterator
from uuid import UUID

from src.agents.routers import (
    RouterRegistry,
    ConversationalRouter,
    RAGRouter,
    QueryClassifier,
)
from src.agents.rag_agent import AgenticRAG


class OrchestratorAgent:
    """Orchestrator that uses multi-stage routing to dispatch queries.

    Routing stages:
    1. Quick Filter: Keyword-based confidence check
    2. LLM Classification: Intent detection for complex queries
    3. Router Dispatch: Map intent to appropriate handler
    """

    def __init__(
        self,
        rag_agent: AgenticRAG | None = None,
        classifier: QueryClassifier | None = None,
        auto_register: bool = True,
    ):
        """Initialize orchestrator with router registry.

        Args:
            rag_agent: Optional RAG agent for RAGRouter
            classifier: Optional query classifier
            auto_register: If True, automatically register default routers
        """
        if auto_register:
            self._setup_routers(rag_agent, classifier)

    def _setup_routers(
        self,
        rag_agent: AgenticRAG | None = None,
        classifier: QueryClassifier | None = None,
    ) -> None:
        """Set up default routers.

        Args:
            rag_agent: Optional RAG agent
            classifier: Optional classifier
        """
        # Clear any existing routers
        RouterRegistry.clear()

        # Register conversational router
        RouterRegistry.register(ConversationalRouter())

        # Register RAG router
        RouterRegistry.register(RAGRouter(rag_agent=rag_agent))

        # Set up classifier
        if classifier:
            RouterRegistry.set_classifier(classifier)

    async def query(
        self,
        user_query: str,
        user_id: UUID | str = "default",
    ) -> dict[str, Any]:
        """Route query using multi-stage strategy and return result.

        Args:
            user_query: User's query
            user_id: User ID for filtering

        Returns:
            Dict with answer, status, latency_ms, and metadata
        """
        t0 = time.perf_counter()

        result = await RouterRegistry.route(user_query, user_id)

        # Ensure latency is tracked
        if "latency_ms" not in result:
            result["latency_ms"] = (time.perf_counter() - t0) * 1000

        return result

    async def query_stream(
        self,
        user_query: str,
        user_id: UUID | str = "default",
    ) -> AsyncIterator[dict]:
        """Route query with streaming response.

        Args:
            user_query: User's query
            user_id: User ID for filtering

        Yields:
            Dict chunks with type:
            - "routing": {router, intent, confidence}
            - "retrieval": {iteration, strategy, docs_retrieved, new_docs, sufficient}
            - "content": {text}
            - "metadata": {status, citations, sources, latency_ms}
        """
        t0 = time.perf_counter()

        async for chunk in RouterRegistry.route_stream(user_query, user_id):
            # Add latency_ms to final metadata
            if chunk.get("type") == "metadata" and "latency_ms" not in chunk.get("data", {}):
                chunk["data"]["latency_ms"] = (time.perf_counter() - t0) * 1000
            yield chunk

    def add_router(self, router: Any, name: str | None = None) -> None:
        """Add a custom router to the registry.

        Args:
            router: Router instance implementing BaseRouter interface
            name: Optional router name
        """
        RouterRegistry.register(router, name)

    def list_routers(self) -> list[str]:
        """List all registered routers.

        Returns:
            List of router names
        """
        return RouterRegistry.list_routers()


def create_orchestrator(
    rag_agent: AgenticRAG | None = None,
    classifier: QueryClassifier | None = None,
) -> OrchestratorAgent:
    """Create orchestrator instance with default routers.

    Args:
        rag_agent: Optional RAG agent instance
        classifier: Optional query classifier

    Returns:
        OrchestratorAgent instance with routers registered
    """
    return OrchestratorAgent(
        rag_agent=rag_agent,
        classifier=classifier,
        auto_register=True,
    )


__all__ = ["OrchestratorAgent", "create_orchestrator"]
