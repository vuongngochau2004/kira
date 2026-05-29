"""Orchestrator agent for routing queries to appropriate handlers."""

import time
from typing import Any
from uuid import UUID

from src.agents.rag_agent import AgenticRAG
from src.agents.llm import chat_async
from src.agents.prompts import CONVERSATIONAL_PROMPT
from src.agents.utils import is_conversational_query
from config.config import settings


class OrchestratorAgent:
    """Orchestrator that routes queries to RAG or conversational handler."""

    def __init__(
        self,
        rag_agent: AgenticRAG | None = None,
        max_retries: int = 2,
    ):
        """Initialize orchestrator.

        Args:
            rag_agent: RAG agent for research queries
            max_retries: Max retry attempts for LLM calls
        """
        self.rag_agent = rag_agent
        self.max_retries = max_retries

    async def _respond_conversationally(self, query: str) -> str:
        """Generate conversational response with retry.

        Args:
            query: User query

        Returns:
            Friendly response or fallback message
        """
        prompt = CONVERSATIONAL_PROMPT.format(query=query)

        for attempt in range(self.max_retries + 1):
            try:
                response = await chat_async(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=200,
                )
                return response["content"]
            except Exception as e:
                if attempt == self.max_retries:
                    return "Xin lỗi, tôi không thể trả lời ngay lúc này."

    async def query(
        self,
        user_query: str,
        user_id: UUID | str = "default",
    ) -> dict[str, Any]:
        """Route query and return result with logging.

        Args:
            user_query: User's query
            user_id: User ID for filtering

        Returns:
            Dict with answer, status, latency_ms
        """
        t0 = time.perf_counter()

        if is_conversational_query(user_query):
            answer = await self._respond_conversationally(user_query)
            return {
                "content": answer,
                "status": "conversational",
                "retrieval_history": [],
                "latency_ms": (time.perf_counter() - t0) * 1000,
            }

        # RAG query
        if self.rag_agent is None:
            self.rag_agent = AgenticRAG(
                max_iterations=3,
                retrieval_k=settings.retrieval_k,
            )

        try:
            result = await self.rag_agent.query(user_query, user_id)
            result["latency_ms"] = (time.perf_counter() - t0) * 1000
            return result
        except Exception as e:
            return {
                "content": "Có lỗi xảy ra khi xử lý câu hỏi.",
                "status": "error",
                "error": str(e),
                "retrieval_history": [],
                "latency_ms": (time.perf_counter() - t0) * 1000,
            }


def create_orchestrator(rag_agent: AgenticRAG | None = None) -> OrchestratorAgent:
    """Create orchestrator instance.

    Args:
        rag_agent: Optional RAG agent instance

    Returns:
        OrchestratorAgent instance
    """
    return OrchestratorAgent(rag_agent=rag_agent)


__all__ = ["OrchestratorAgent", "create_orchestrator"]
