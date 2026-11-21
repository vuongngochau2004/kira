"""Routing policy for the compiled personal-document RAG workflow."""

import time
from typing import Any

from loguru import logger

from kira.chat.rag.state import (
    AgentStatus,
    OrchestratorAgentConfig,
    RAGState,
    create_agent_result,
    mark_agent_start,
    update_orchestrator_routing,
    update_state_with_agent_result,
)


class OrchestratorAgent:
    """Select the graph's first node without running a second agent loop."""

    def __init__(self, config: OrchestratorAgentConfig) -> None:
        """Initialize routing policy."""
        self.config = config

    async def handle(self, state: RAGState, context: dict[str, Any] | None = None) -> RAGState:
        """Record the initial routing decision for LangGraph."""
        started = time.perf_counter()
        state = mark_agent_start(state, "OrchestratorAgent")
        if not self.can_handle(state):
            logger.warning("RAG routing received an invalid request state")
            state["should_fallback"] = True
            state["fallback_reason"] = "invalid_request_state"
            decision = "fallback"
            status = AgentStatus.FAILED
        else:
            decision = "RetrievalAgent"
            state = update_orchestrator_routing(
                state,
                decision,
                {
                    "next_agent": decision,
                    "reasoning": "Standard personal-document workflow",
                    "query_complexity": "medium" if len(state["query"]) > 50 else "simple",
                },
            )
            status = AgentStatus.COMPLETED

        result = create_agent_result(
            agent_name="OrchestratorAgent",
            status=status,
            execution_time_ms=(time.perf_counter() - started) * 1000,
            metadata={"next_agent": decision},
        )
        return update_state_with_agent_result(state, result)

    @staticmethod
    def can_handle(state: RAGState) -> bool:
        """Require a query and authenticated user scope before retrieval."""
        return bool(state.get("query") and state.get("user_id"))
