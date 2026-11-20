"""
LangGraph-based RAG Pipeline

Replaces custom OrchestratorAgent with LangGraph StateGraph architecture.
Provides better visualization, debugging, and state management.

Architecture:
    Entry Point → Orchestrator Node → Retrieval Node → Generation Node
                                          ↓
                                    Quality Node → [Conditional Edge]
                                          ↓
                              [Regenerate] or [END]
"""

import asyncio
from contextlib import aclosing
from typing import Literal, Optional
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
from langgraph.graph import END, StateGraph
from loguru import logger

from kira.chat.history import ConversationTurn, bound_history
from kira.chat.rag.nodes.generation import GenerationAgent
from kira.chat.rag.nodes.orchestrator import OrchestratorAgent
from kira.chat.rag.nodes.quality import QualityAgent
from kira.chat.rag.nodes.retrieval import RetrievalAgent
from kira.chat.rag.state import (
    GenerationAgentConfig,
    OrchestratorAgentConfig,
    QualityAgentConfig,
    RAGState,
    RetrievalAgentConfig,
    create_initial_state,
    get_quality_score,
    should_regenerate,
)
from kira.core.request_trace import request_stage
from kira.providers.embedding.base import EmbeddingPort
from kira.providers.llm.base import LLMPort
from kira.retrieval.search import SearchUseCase


class LangGraphRAGPipeline:
    """
    LangGraph-based RAG pipeline.

    Replaces custom OrchestratorAgent with StateGraph architecture.
    Reuses existing agent logic as node functions.

    Benefits:
    - Visual graph representation
    - Built-in state checkpointing
    - Better debugging tools
    - Battle-tested orchestration
    """

    def __init__(
        self,
        orchestrator_config: OrchestratorAgentConfig,
        retrieval_config: RetrievalAgentConfig,
        generation_config: GenerationAgentConfig,
        quality_config: QualityAgentConfig,
        embedding: EmbeddingPort | None = None,
        search: SearchUseCase | None = None,
        llm: LLMPort | None = None,
    ):
        """
        Initialize LangGraph RAG pipeline.

        Args:
            orchestrator_config: Configuration for orchestrator node
            retrieval_config: Configuration for retrieval node
            generation_config: Configuration for generation node
            quality_config: Configuration for quality node
            embedding: Embedding port for retrieval
            search: Retrieval application service
            llm: LLM port for generation and quality agents
        """
        self.orchestrator_config = orchestrator_config
        self.retrieval_config = retrieval_config
        self.generation_config = generation_config
        self.quality_config = quality_config
        self.llm = llm

        # Initialize agents (reuse existing implementations)
        self.orchestrator_agent = OrchestratorAgent(orchestrator_config)
        self.retrieval_agent = RetrievalAgent(
            retrieval_config,
            llm_client=llm,
            embedding=embedding,
            search=search,
        )
        self.generation_agent = GenerationAgent(generation_config, llm_client=llm)
        self.quality_agent = QualityAgent(quality_config, llm_client=llm)

        # Build and compile graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        Build LangGraph StateGraph for RAG pipeline.

        Graph Structure:
            START → orchestrator → retrieval → generation → quality
                                                   ↓
                                            [conditional edge]
                                                   ↓
                                      [regenerate → generation]
                                      or
                                      [END]

        Returns:
            Compiled StateGraph ready for invocation
        """
        # Create state graph with RAGState
        graph = StateGraph(RAGState)

        # Add nodes (reuse existing agent logic)
        graph.add_node("orchestrator", self._orchestrator_node)
        graph.add_node("retrieval", self._retrieval_node)
        graph.add_node("generation", self._generation_node)
        graph.add_node("quality", self._quality_node)

        # Define entry point
        graph.set_entry_point("orchestrator")

        # Add conditional edge: orchestrator → retrieval or fallback
        graph.add_conditional_edges(
            "orchestrator",
            self._should_route_to_retrieval,
            {"retrieval": "retrieval", "fallback": END},
        )

        # Add fixed edge: retrieval → generation
        graph.add_edge("retrieval", "generation")

        # Add fixed edge: generation → quality
        graph.add_edge("generation", "quality")

        # Add conditional edge: quality → regenerate or END
        graph.add_conditional_edges(
            "quality", self._should_regenerate_or_finish, {"regenerate": "generation", "end": END}
        )

        # Compile graph
        compiled_graph = graph.compile()

        logger.info("✅ LangGraph RAG pipeline compiled successfully")
        return compiled_graph

    # ==============================================================================
    # Node Functions (reuse existing agent logic)
    # ==============================================================================

    async def _orchestrator_node(self, state: RAGState) -> RAGState:
        """
        Orchestrator node - Initial routing and decision making.

        Reuses OrchestratorAgent.handle() logic.

        Args:
            state: Current RAGState

        Returns:
            Updated RAGState with routing decision
        """
        logger.info("🎯 <yellow>[RAG NODE: ORCHESTRATOR]</yellow> Orchestrator node executing...")
        with request_stage("orchestrator"):
            async with asyncio.timeout(self.orchestrator_config.timeout_ms / 1000):
                return await self.orchestrator_agent.handle(state, context={"langgraph_node": True})

    async def _retrieval_node(self, state: RAGState, config: RunnableConfig) -> RAGState:
        """
        Retrieval node - Query refinement + retrieval + reranking.

        Reuses RetrievalAgent.handle() logic.

        Args:
            state: Current RAGState

        Returns:
            Updated RAGState with retrieved documents
        """
        logger.info("🔍 <yellow>[RAG NODE: RETRIEVAL]</yellow> Retrieval node executing...")
        if config.get("configurable", {}).get("stream_preview"):
            get_stream_writer()({"kind": "stage_start", "stage": "retrieval"})
        with request_stage("retrieval"):
            async with asyncio.timeout(self.retrieval_config.timeout_ms / 1000):
                return await self.retrieval_agent.handle(state, context={"langgraph_node": True})

    async def _generation_node(self, state: RAGState, config: RunnableConfig) -> RAGState:
        """
        Generation node - LLM response generation with citations.

        Reuses GenerationAgent.handle() logic.

        Args:
            state: Current RAGState

        Returns:
            Updated RAGState with generated response
        """
        logger.info("✍️  <yellow>[RAG NODE: GENERATION]</yellow> Generation node executing...")
        attempt = state["orchestrator_state"].get("iteration_count", 0) + 1
        feedback: str | None = None
        if attempt > 1:
            quality = state["quality_agent_output"]
            critique = quality.get("critique") or {}
            feedback_items = [*critique.get("issues", []), *quality.get("suggestions", [])]
            feedback = "\n".join(feedback_items) or "Improve factual support and citations."

        with request_stage("generation"):
            async with asyncio.timeout(self.generation_config.timeout_ms / 1000):
                if config.get("configurable", {}).get("stream_preview"):
                    writer = get_stream_writer()
                    writer({"kind": "attempt_start", "attempt": attempt})
                    state = await self.generation_agent.generate_for_graph_stream(
                        state,
                        on_token=lambda token: writer(
                            {"kind": "token", "attempt": attempt, "text": token}
                        ),
                        feedback=feedback,
                    )
                elif feedback is not None:
                    state = await self.generation_agent.regenerate_with_feedback(
                        state, feedback=feedback
                    )
                else:
                    state = await self.generation_agent.handle(
                        state, context={"langgraph_node": True}
                    )
        if state.get("generated_response") and not state.get("final_response"):
            state["final_response"] = state["generated_response"]
        return state

    async def _quality_node(self, state: RAGState, config: RunnableConfig) -> RAGState:
        """
        Quality node - Critique + verification + quality assessment.

        Reuses QualityAgent.handle() logic.

        Args:
            state: Current RAGState

        Returns:
            Updated RAGState with quality assessment
        """
        logger.info("🎓 <yellow>[RAG NODE: QUALITY]</yellow> Quality node executing...")
        if config.get("configurable", {}).get("stream_preview"):
            get_stream_writer()({"kind": "stage_start", "stage": "quality"})
        with request_stage("quality"):
            async with asyncio.timeout(self.quality_config.timeout_ms / 1000):
                state = await self.quality_agent.handle(state, context={"langgraph_node": True})
        quality = state["quality_agent_output"]
        verification = quality.get("verification") or {}
        verified = verification.get("is_verified") is True
        passed = (
            get_quality_score(state) >= self.orchestrator_config.quality_gate_threshold
            and verified
            and not should_regenerate(state)
        )
        if passed:
            state["is_final"] = True
            state["routing_decision"] = "end"
            return state

        attempts = state["orchestrator_state"].get("iteration_count", 0) + 1
        if attempts < self.orchestrator_config.max_pipeline_iterations:
            state["orchestrator_state"]["iteration_count"] = attempts
            state["routing_decision"] = "regenerate"
            return state

        state["should_fallback"] = True
        state["fallback_reason"] = "verification_failed" if not verified else "quality_gate_failed"
        state["final_response"] = ""
        state["final_citations"] = []
        state["routing_decision"] = "end"
        return state

    # ==============================================================================
    # Conditional Edge Functions (routing logic)
    # ==============================================================================

    async def _should_route_to_retrieval(self, state: RAGState) -> Literal["retrieval", "fallback"]:
        """
        Conditional edge: Decide routing after orchestrator.

        Args:
            state: Current RAGState

        Returns:
            "retrieval" if normal flow, "fallback" if should fallback
        """
        # Check if fallback triggered
        if state.get("should_fallback"):
            logger.warning(
                f"🔄 <yellow>[RAG ROUTING]</yellow> Orchestrator triggered fallback! "
                f"Reason: {state.get('fallback_reason')}"
            )
            return "fallback"

        # Normal flow: proceed to retrieval
        logger.info("→ <yellow>[RAG ROUTING]</yellow> Routing to retrieval node")
        return "retrieval"

    async def _should_regenerate_or_finish(self, state: RAGState) -> Literal["regenerate", "end"]:
        """
        Conditional edge: Decide whether to regenerate or finish.

        Quality routing is decided by the quality node and stored in state.

        Args:
            state: Current RAGState

        Returns:
            "regenerate" if should retry, "end" if finished
        """
        quality_score = get_quality_score(state)
        threshold = self.orchestrator_config.quality_gate_threshold

        iteration = state["orchestrator_state"].get("iteration_count", 0)
        max_iterations = self.orchestrator_config.max_pipeline_iterations

        logger.info(
            f"🎯 <cyan>[RAG QUALITY GATE]</cyan> Quality Gate check: score={quality_score:.2f}, "
            f"threshold={threshold:.2f}, iteration={iteration}/{max_iterations}"
        )

        logger.info(
            "RAG quality routing: score={:.2f} threshold={:.2f} iteration={}/{} decision={}",
            quality_score,
            threshold,
            iteration,
            max_iterations,
            state["routing_decision"],
        )
        return "regenerate" if state["routing_decision"] == "regenerate" else "end"

    # ==============================================================================
    # Public API
    # ==============================================================================

    async def run(
        self,
        query: str,
        user_id: str,
        conversation_id: Optional[UUID] = None,
        history: list[ConversationTurn] | None = None,
    ) -> RAGState:
        """
        Run the LangGraph RAG pipeline.

        Args:
            query: User's query
            user_id: User ID
            conversation_id: Optional conversation ID for context

        Returns:
            Final RAGState with response and citations
        """
        logger.info("RAG pipeline starting: user_id={}, query_chars={}", user_id, len(query))

        # Create initial state
        initial_state = create_initial_state(
            query, user_id, conversation_id, bound_history(history)
        )

        # Invoke graph
        try:
            result = await self.graph.ainvoke(initial_state)
            logger.info(
                "✅ <green>[RAG PIPELINE COMPLETED]</green> LangGraph RAG pipeline execution finished successfully."
            )
            return result

        except Exception:
            logger.error("LangGraph pipeline failed")
            # Return error state
            initial_state["errors"].append("rag_pipeline_failed")
            initial_state["should_fallback"] = True
            initial_state["fallback_reason"] = "rag_pipeline_failed"
            return initial_state

    async def run_stream(
        self,
        query: str,
        user_id: str,
        conversation_id: Optional[UUID] = None,
        history: list[ConversationTurn] | None = None,
    ):
        """
        Run the LangGraph RAG pipeline with streaming updates.

        Yields state updates from each node execution.

        Args:
            query: User's query
            user_id: User ID
            conversation_id: Optional conversation ID for context

        Yields:
            Streaming updates from graph execution
        """
        logger.info("RAG stream starting: user_id={}, query_chars={}", user_id, len(query))

        initial_state = create_initial_state(
            query, user_id, conversation_id, bound_history(history)
        )

        try:
            # A previous implementation manually invoked each agent here. That
            # duplicated graph behaviour and, critically, skipped the quality
            # gate's ``generation -> quality -> generation`` regeneration loop.
            # Streaming must execute the same compiled workflow as ``run``.
            async with aclosing(
                self.graph.astream(
                    initial_state,
                    config={"configurable": {"stream_preview": True}},
                    stream_mode=["updates", "custom"],
                )
            ) as stream:
                async for mode, chunk in stream:
                    yield {"mode": mode, "chunk": chunk}
        except Exception:
            logger.error("LangGraph streaming failed")
            yield {"mode": "error", "chunk": {"error": "rag_pipeline_failed"}}

    def get_graph_visualization(self) -> str:
        """
        Get ASCII visualization of the graph structure.

        Returns:
            ASCII string representation of the graph
        """
        try:
            return self.graph.get_graph().print_ascii()
        except Exception as e:
            logger.error(f"Failed to generate graph visualization: {e}")
            return "Failed to generate visualization"


# ==============================================================================
# Factory Function
# ==============================================================================


def create_langgraph_pipeline(
    orchestrator_config: Optional[OrchestratorAgentConfig] = None,
    retrieval_config: Optional[RetrievalAgentConfig] = None,
    generation_config: Optional[GenerationAgentConfig] = None,
    quality_config: Optional[QualityAgentConfig] = None,
    embedding: EmbeddingPort | None = None,
    search: SearchUseCase | None = None,
    llm: LLMPort | None = None,
) -> LangGraphRAGPipeline:
    """
    Factory function to create LangGraph RAG pipeline.

    Args:
        orchestrator_config: Optional orchestrator configuration
        retrieval_config: Optional retrieval configuration
        generation_config: Optional generation configuration
        quality_config: Optional quality configuration
        embedding: Embedding port for retrieval
        search: Retrieval application service
        llm: LLM port for generation and quality agents

    Returns:
        Configured LangGraphRAGPipeline instance
    """
    # Use defaults if not provided
    orchestrator_config = orchestrator_config or OrchestratorAgentConfig()
    retrieval_config = retrieval_config or RetrievalAgentConfig()
    generation_config = generation_config or GenerationAgentConfig()
    quality_config = quality_config or QualityAgentConfig()

    return LangGraphRAGPipeline(
        orchestrator_config=orchestrator_config,
        retrieval_config=retrieval_config,
        generation_config=generation_config,
        quality_config=quality_config,
        embedding=embedding,
        search=search,
        llm=llm,
    )
