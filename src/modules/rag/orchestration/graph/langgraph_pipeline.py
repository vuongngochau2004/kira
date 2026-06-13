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

from loguru import logger
from typing import Literal, Optional
from uuid import UUID

from langgraph.graph import StateGraph, END

from src.modules.rag.orchestration.state.rag_state import (
    RAGState,
    create_initial_state,
    OrchestratorAgentConfig,
    RetrievalAgentConfig,
    GenerationAgentConfig,
    QualityAgentConfig,
    get_quality_score,
    should_regenerate,
    increment_orchestrator_iteration,
)
from src.modules.rag.orchestration.agents.orchestrator_agent import OrchestratorAgent
from src.modules.rag.orchestration.agents.retrieval_agent import RetrievalAgent
from src.modules.rag.orchestration.agents.generation_agent import GenerationAgent
from src.modules.rag.orchestration.agents.quality_agent import QualityAgent
from src.modules.retrieval.application.search_use_case import SearchUseCase
from src.shared.ports.embedding import EmbeddingPort
from src.shared.ports.llm import LLMPort


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
            {
                "retrieval": "retrieval",
                "fallback": END
            }
        )

        # Add fixed edge: retrieval → generation
        graph.add_edge("retrieval", "generation")

        # Add fixed edge: generation → quality
        graph.add_edge("generation", "quality")

        # Add conditional edge: quality → regenerate or END
        graph.add_conditional_edges(
            "quality",
            self._should_regenerate_or_finish,
            {
                "regenerate": "generation",
                "end": END
            }
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
        return await self.orchestrator_agent.handle(state, context={"langgraph_node": True})

    async def _retrieval_node(self, state: RAGState) -> RAGState:
        """
        Retrieval node - Query refinement + retrieval + reranking.

        Reuses RetrievalAgent.handle() logic.

        Args:
            state: Current RAGState

        Returns:
            Updated RAGState with retrieved documents
        """
        logger.info("🔍 <yellow>[RAG NODE: RETRIEVAL]</yellow> Retrieval node executing...")
        return await self.retrieval_agent.handle(state, context={"langgraph_node": True})

    async def _generation_node(self, state: RAGState) -> RAGState:
        """
        Generation node - LLM response generation with citations.

        Reuses GenerationAgent.handle() logic.

        Args:
            state: Current RAGState

        Returns:
            Updated RAGState with generated response
        """
        logger.info("✍️  <yellow>[RAG NODE: GENERATION]</yellow> Generation node executing...")
        state = await self.generation_agent.handle(state, context={"langgraph_node": True})
        if state.get("generated_response") and not state.get("final_response"):
            state["final_response"] = state["generated_response"]
        return state

    async def _quality_node(self, state: RAGState) -> RAGState:
        """
        Quality node - Critique + verification + quality assessment.

        Reuses QualityAgent.handle() logic.

        Args:
            state: Current RAGState

        Returns:
            Updated RAGState with quality assessment
        """
        logger.info("🎓 <yellow>[RAG NODE: QUALITY]</yellow> Quality node executing...")
        return await self.quality_agent.handle(state, context={"langgraph_node": True})

    # ==============================================================================
    # Conditional Edge Functions (routing logic)
    # ==============================================================================

    def _should_route_to_retrieval(self, state: RAGState) -> Literal["retrieval", "fallback"]:
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

    def _should_regenerate_or_finish(self, state: RAGState) -> Literal["regenerate", "end"]:
        """
        Conditional edge: Decide whether to regenerate or finish.

        Quality gate logic:
        - If quality score >= threshold → END (proceed)
        - If quality score < threshold AND iteration < max → REGENERATE
        - If quality score < threshold AND iteration >= max → END (accept despite low quality)

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

        # Quality gate passed
        if quality_score >= threshold:
            logger.info(f"✅ <green>[RAG QUALITY GATE PASSED]</green> score={quality_score:.2f} >= threshold={threshold:.2f}")
            return "end"

        # Quality failed but max iterations reached
        if iteration >= max_iterations:
            logger.warning(
                f"⚠️  <yellow>[RAG QUALITY GATE MAX ITERATIONS]</yellow> Max iterations reached ({iteration}/{max_iterations}). "
                f"Accepting current response despite low quality (score={quality_score:.2f})"
            )
            return "end"

        # Quality failed and can regenerate
        if should_regenerate(state):
            logger.info(
                f"🔄 <yellow>[RAG QUALITY GATE REGENERATE]</yellow> Regeneration recommended (score={quality_score:.2f} < threshold={threshold:.2f})"
            )
            # Increment iteration counter
            state = increment_orchestrator_iteration(state)
            return "regenerate"

        # Accept despite low quality
        logger.warning(
            f"⚠️  <yellow>[RAG QUALITY GATE LOW QUALITY]</yellow> Accepting low-quality response (score={quality_score:.2f})"
        )
        return "end"

    # ==============================================================================
    # Public API
    # ==============================================================================

    async def run(
        self,
        query: str,
        user_id: str,
        conversation_id: Optional[UUID] = None
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
        logger.info(
            f"🚀 <yellow>[RAG PIPELINE START]</yellow> Starting LangGraph RAG pipeline. "
            f"Query: \"{query[:50] + '...' if len(query) > 50 else query}\", user_id='{user_id}'"
        )

        # Create initial state
        initial_state = create_initial_state(query, user_id, conversation_id)

        # Invoke graph
        try:
            result = await self.graph.ainvoke(initial_state)
            logger.info("✅ <green>[RAG PIPELINE COMPLETED]</green> LangGraph RAG pipeline execution finished successfully.")
            return result

        except Exception as e:
            logger.error(f"❌ <red>[RAG PIPELINE ERROR]</red> LangGraph pipeline failed: {e}", exc_info=True)
            # Return error state
            initial_state["errors"].append(f"LangGraph pipeline error: {str(e)}")
            initial_state["should_fallback"] = True
            initial_state["fallback_reason"] = str(e)
            return initial_state

    async def run_stream(
        self,
        query: str,
        user_id: str,
        conversation_id: Optional[UUID] = None
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
        logger.info(
            f"🚀 <yellow>[RAG PIPELINE STREAM START]</yellow> Starting LangGraph RAG streaming. "
            f"Query: \"{query[:50] + '...' if len(query) > 50 else query}\", user_id='{user_id}'"
        )

        initial_state = create_initial_state(query, user_id, conversation_id)

        try:
            state = await self.orchestrator_agent.handle(
                initial_state,
                context={"langgraph_node": True, "streaming": True},
            )
            yield {"mode": "updates", "chunk": {"orchestrator": state}}

            if state.get("should_fallback"):
                yield {"mode": "updates", "chunk": {"fallback": state}}
                return

            state = await self.retrieval_agent.handle(
                state,
                context={"langgraph_node": True, "streaming": True},
            )
            yield {"mode": "updates", "chunk": {"retrieval": state}}

            generation_final_state = state
            async for generation_chunk in self.generation_agent.handle_stream(
                state,
                context={"langgraph_node": True, "streaming": True},
            ):
                chunk_type = generation_chunk.get("type")
                chunk_data = generation_chunk.get("data", {})

                if chunk_type == "content":
                    text = chunk_data.get("text", "")
                    if text:
                        yield {"mode": "messages", "chunk": text}
                elif chunk_type == "metadata":
                    # handle_stream mutates state in-place and stores the final state
                    # The state object itself is updated, so we just need to track it
                    generation_final_state = state
                elif chunk_type == "error":
                    yield {"mode": "error", "chunk": chunk_data}

            # Use the state that was updated in-place by handle_stream
            state = generation_final_state
            if state.get("generated_response") and not state.get("final_response"):
                state["final_response"] = state["generated_response"]
            yield {"mode": "updates", "chunk": {"generation": state}}

            state = await self.quality_agent.handle(
                state,
                context={"langgraph_node": True, "streaming": True},
            )
            yield {"mode": "updates", "chunk": {"quality": state}}

        except Exception as e:
            logger.error(f"❌ <red>[RAG PIPELINE STREAM ERROR]</red> LangGraph streaming failed: {e}", exc_info=True)
            yield {"mode": "error", "chunk": {"error": str(e)}}

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
