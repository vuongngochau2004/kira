"""
OrchestratorAgent: Coordination and routing (4-agent architecture)

This agent is the central coordinator for the agentic RAG system:
- Routing decisions (which agent to execute next)
- Flow control (proceed, retry, regenerate, or fallback)
- Agent pipeline management
- Quality gate enforcement
- Error handling and fallback logic

Architecture:
    Input: RAGState (query, user_id)
    Stage 1: Analyze query and determine routing
    Stage 2: Execute agent pipeline
    Stage 3: Evaluate quality and make final decision
    Output: RAGState with final_response

Example:
    agent = OrchestratorAgent(config=OrchestratorAgentConfig(), container=di_container)
    state = await agent.handle(state)
    final_response = state["final_response"]
"""

import inspect
from typing import List, Dict, Any, AsyncIterator, Optional, Callable
from uuid import UUID
import time

from src.modules.rag.domain.state.rag_state import (
    RAGState,
    AgentResult,
    AgentStatus,
    OrchestratorAgentConfig,
    create_agent_result,
    mark_agent_start,
    update_state_with_agent_result,
    update_orchestrator_routing,
    increment_orchestrator_iteration,
    get_quality_score,
    should_regenerate
)
from src.shared.kernel.interfaces.handlers import QueryHandlerBase
from src.shared.kernel.interfaces.classification import Intent, ClassificationResult
from loguru import logger


class OrchestratorAgent:
    """
    Central orchestrator for agentic RAG pipeline.

    The OrchestratorAgent manages the entire workflow:
    1. Analyzes incoming queries
    2. Routes to appropriate agents
    3. Manages execution flow (retries, regeneration)
    4. Enforces quality gates
    5. Handles errors and fallbacks

    This is NEW in the 4-agent architecture, replacing the loose
    coordination between agents with centralized control.

    Attributes:
        config: OrchestratorAgentConfig
        retrieval_agent: RetrievalAgent instance
        generation_agent: GenerationAgent instance
        quality_agent: QualityAgent instance
    """

    def __init__(
        self,
        config: OrchestratorAgentConfig,
        retrieval_agent: Optional[QueryHandlerBase] = None,
        generation_agent: Optional[QueryHandlerBase] = None,
        quality_agent: Optional[QueryHandlerBase] = None
    ):
        """
        Initialize OrchestratorAgent.

        Args:
            config: Orchestrator configuration
            retrieval_agent: RetrievalAgent instance
            generation_agent: GenerationAgent instance
            quality_agent: QualityAgent instance
        """
        self.config = config
        self.retrieval_agent = retrieval_agent
        self.generation_agent = generation_agent
        self.quality_agent = quality_agent

    async def handle(
        self,
        state: RAGState,
        context: Optional[Dict[str, Any]] = None
    ) -> RAGState:
        """
        Execute complete agentic RAG pipeline with orchestration.

        This is the main entry point. It orchestrates the entire workflow:
        1. Initial routing decision
        2. Execute RetrievalAgent
        3. Execute GenerationAgent
        4. Execute QualityAgent
        5. Evaluate quality and decide (proceed, regenerate, or fallback)

        Args:
            state: Current RAGState with query and user_id
            context: Optional additional context

        Returns:
            Updated RAGState with final_response
        """
        start_time = time.time()
        state = mark_agent_start(state, "OrchestratorAgent")

        try:
            query = state["query"]
            user_id = state["user_id"]

            logger.info(
                f"🚀 <yellow>[ORCHESTRATOR agent START]</yellow> Starting OrchestratorAgent. "
                f"Query: \"{query[:50] + '...' if len(query) > 50 else query}\", user_id='{user_id}'"
            )

            # Stage 1: Initial routing
            routing_decision = await self._make_routing_decision(state)
            state = update_orchestrator_routing(state, routing_decision["next_agent"], routing_decision)
            logger.info(f"🎯 <yellow>[ORCHESTRATOR ROUTING]</yellow> Initial routing decision: next_agent={routing_decision['next_agent']}")

            if context and context.get("langgraph_node"):
                logger.info("🎯 <yellow>[ORCHESTRATOR ROUTING]</yellow> LangGraph node mode: bypassing execution loop.")
                execution_time = (time.time() - start_time) * 1000
                result = create_agent_result(
                    agent_name="OrchestratorAgent",
                    status=AgentStatus.COMPLETED,
                    execution_time_ms=execution_time,
                    metadata={"langgraph_node": True, "next_agent": routing_decision["next_agent"]}
                )
                return update_state_with_agent_result(state, result)

            # Stage 2: Execute pipeline with quality control
            max_iterations = self.config.max_pipeline_iterations
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                logger.info(f"🔄 <yellow>[ORCHESTRATOR ITERATION]</yellow> Pipeline iteration {iteration}/{max_iterations}")

                # Execute RetrievalAgent
                if self.retrieval_agent:
                    state = await self._execute_agent(state, self.retrieval_agent, "RetrievalAgent")

                # Execute GenerationAgent
                if self.generation_agent:
                    state = await self._execute_agent(state, self.generation_agent, "GenerationAgent")

                # Execute QualityAgent
                if self.quality_agent:
                    state = await self._execute_agent(state, self.quality_agent, "QualityAgent")

                # Evaluate quality
                quality_score = get_quality_score(state)
                logger.info(f"📊 <cyan>[ORCHESTRATOR QUALITY]</cyan> Iteration {iteration} quality score: {quality_score:.2f}")

                # Quality gate check
                if quality_score >= self.config.quality_gate_threshold:
                    logger.info(f"✅ <green>[ORCHESTRATOR QUALITY PASSED]</green> Quality gate passed: {quality_score:.2f} >= threshold={self.config.quality_gate_threshold:.2f}")
                    state["final_response"] = state["generated_response"]
                    state["is_final"] = True
                    break

                # Check if should regenerate
                if should_regenerate(state) and iteration < max_iterations:
                    logger.info("🔄 <yellow>[ORCHESTRATOR REGENERATE]</yellow> Quality gate failed. Regeneration recommended, retrying...")
                    state = increment_orchestrator_iteration(state)
                    continue

                # Quality failed, check fallback
                if quality_score < self.config.quality_gate_threshold:
                    logger.warning(f"⚠️  <yellow>[ORCHESTRATOR QUALITY FAILED]</yellow> Quality gate failed after {iteration} iterations (score={quality_score:.2f} < threshold={self.config.quality_gate_threshold:.2f})")
                    if self.config.enable_routing and self.config.enable_flow_control:
                        # Fallback to simpler pipeline
                        state = await self._fallback_pipeline(state)
                        break
                    else:
                        # Accept current response despite low quality
                        state["final_response"] = state["generated_response"]
                        state["is_final"] = True
                        break

            # Finalize
            if not state.get("is_final"):
                state["final_response"] = state["generated_response"]
                state["is_final"] = True

            execution_time = (time.time() - start_time) * 1000
            result = create_agent_result(
                agent_name="OrchestratorAgent",
                status=AgentStatus.COMPLETED,
                execution_time_ms=execution_time,
                metadata={
                    "iterations": iteration,
                    "final_quality": get_quality_score(state),
                    "routing_history": len(state["orchestrator_state"]["routing_history"]),
                    "total_time_ms": execution_time
                }
            )

            logger.info(f"✅ <green>[ORCHESTRATOR agent COMPLETED]</green> Completed in {execution_time:.0f}ms after {iteration} iterations")
            return update_state_with_agent_result(state, result)

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"❌ <red>[ORCHESTRATOR agent ERROR]</red> OrchestratorAgent failed: {e}", exc_info=True)

            result = create_agent_result(
                agent_name="OrchestratorAgent",
                status=AgentStatus.FAILED,
                execution_time_ms=execution_time,
                error_message=str(e)
            )

            state = update_state_with_agent_result(state, result)
            state["should_fallback"] = True
            state["fallback_reason"] = str(e)
            return state

    async def handle_stream(
        self,
        state: RAGState,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute pipeline with streaming updates.

        Yields progress updates for each stage and agent execution.

        Args:
            state: Current RAGState
            context: Optional additional context

        Yields:
            Streaming chunks with orchestration progress
        """
        start_time = time.time()
        state = mark_agent_start(state, "OrchestratorAgent")

        try:
            yield {"type": "routing", "data": {"status": "started"}}

            # Initial routing
            routing_decision = await self._make_routing_decision(state)
            state = update_orchestrator_routing(state, routing_decision["next_agent"], routing_decision)

            yield {
                "type": "routing",
                "data": {
                    "status": "completed",
                    "next_agent": routing_decision["next_agent"],
                    "reasoning": routing_decision.get("reasoning", "")
                }
            }

            # Execute pipeline
            max_iterations = self.config.max_pipeline_iterations
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                yield {"type": "iteration", "data": {"iteration": iteration, "max": max_iterations}}

                # Execute agents
                if self.retrieval_agent:
                    yield {"type": "agent", "data": {"agent": "RetrievalAgent", "status": "started"}}
                    state = await self._execute_agent(state, self.retrieval_agent, "RetrievalAgent")
                    yield {"type": "agent", "data": {"agent": "RetrievalAgent", "status": "completed"}}

                if self.generation_agent:
                    yield {"type": "agent", "data": {"agent": "GenerationAgent", "status": "started"}}
                    # For streaming generation, we'd need to handle streaming differently
                    state = await self._execute_agent(state, self.generation_agent, "GenerationAgent")
                    yield {"type": "agent", "data": {"agent": "GenerationAgent", "status": "completed"}}

                if self.quality_agent:
                    yield {"type": "agent", "data": {"agent": "QualityAgent", "status": "started"}}
                    state = await self._execute_agent(state, self.quality_agent, "QualityAgent")

                    quality_score = get_quality_score(state)
                    yield {
                        "type": "agent",
                        "data": {
                            "agent": "QualityAgent",
                            "status": "completed",
                            "quality_score": quality_score
                        }
                    }

                    # Quality gate check
                    if quality_score >= self.config.quality_gate_threshold:
                        yield {
                            "type": "quality_gate",
                            "data": {
                                "passed": True,
                                "score": quality_score,
                                "threshold": self.config.quality_gate_threshold
                            }
                        }
                        break
                    elif should_regenerate(state) and iteration < max_iterations:
                        yield {
                            "type": "quality_gate",
                            "data": {
                                "passed": False,
                                "score": quality_score,
                                "action": "regenerate"
                            }
                        }
                        continue
                    else:
                        yield {
                            "type": "quality_gate",
                            "data": {
                                "passed": False,
                                "score": quality_score,
                                "action": "accept"
                            }
                        }
                        break

            # Finalize
            state["final_response"] = state["generated_response"]
            state["is_final"] = True

            execution_time = (time.time() - start_time) * 1000
            result = create_agent_result(
                agent_name="OrchestratorAgent",
                status=AgentStatus.COMPLETED,
                execution_time_ms=execution_time
            )
            state = update_state_with_agent_result(state, result)

            yield {"type": "done", "data": {"iterations": iteration, "total_time_ms": execution_time}}

        except Exception as e:
            logger.error(f"OrchestratorAgent streaming failed: {e}")
            yield {"type": "error", "data": {"message": str(e)}}

    def can_handle(self, state: RAGState) -> bool:
        """
        Check if orchestrator can handle the current state.

        Orchestrator handles all valid RAG states with queries.

        Args:
            state: Current RAGState

        Returns:
            True if state has required fields
        """
        return bool(state.get("query") and state.get("user_id"))

    # ==========================================================================
    # Routing and Decision Making
    # ==========================================================================

    async def _make_routing_decision(self, state: RAGState) -> Dict[str, Any]:
        """
        Make routing decision for pipeline execution.

        TODO: Implement intelligent routing based on:
        - Query complexity analysis
        - User historical patterns
        - System load balancing

        Args:
            state: Current RAGState

        Returns:
            Routing decision with next_agent and reasoning
        """
        query = state["query"]
        query_length = len(query)

        # TODO: Implement sophisticated routing logic
        # For now, always route through full pipeline
        return {
            "next_agent": "RetrievalAgent",
            "reasoning": "Standard query - full pipeline",
            "query_complexity": "medium" if 50 < query_length < 200 else "simple"
        }

    async def _execute_agent(
        self,
        state: RAGState,
        agent: QueryHandlerBase,
        agent_name: str
    ) -> RAGState:
        """
        Execute an agent and handle errors.

        Multi-Agent agents expect RAGState directly with (state, context) signature.
        This method adapts to both QueryHandlerBase and Multi-Agent interfaces.

        Args:
            state: Current RAGState
            agent: Agent instance to execute
            agent_name: Name of agent for logging

        Returns:
            Updated RAGState
        """
        try:
            # Multi-Agent agents expect RAGState directly
            # Check agent signature by inspecting handle method
            import inspect

            handle_sig = inspect.signature(agent.handle)
            handle_params = list(handle_sig.parameters.keys())

            # Multi-Agent interface: handle(state, context=None)
            if len(handle_params) >= 1 and handle_params[0] in ['state', 'self']:
                # Multi-Agent agent - pass RAGState directly
                logger.debug(f"Executing {agent_name} with Multi-Agent interface")
                state = await agent.handle(state, context={"orchestrator": True})
            else:
                # QueryHandlerBase interface - pass (query, user_id, classification)
                logger.debug(f"Executing {agent_name} with QueryHandlerBase interface")
                classification = ClassificationResult(
                    intent=Intent.RAG,
                    confidence=0.8,
                    reasoning="Orchestrator routing"
                )
                state = await agent.handle(state["query"], state["user_id"], classification)

            return state

        except Exception as e:
            logger.error(f"Agent {agent_name} execution failed: {e}", exc_info=True)

            # Add error to state
            state["errors"].append(f"{agent_name} failed: {str(e)}")

            return state

    async def _fallback_pipeline(self, state: RAGState) -> RAGState:
        """
        Execute fallback pipeline when quality gate fails.

        TODO: Implement fallback strategies:
        - Simple retrieval without reranking
        - Direct LLM generation without retrieval
        - Cached responses

        Args:
            state: Current RAGState

        Returns:
            Updated RAGState with fallback response
        """
        logger.warning("Executing fallback pipeline")

        # TODO: Implement actual fallback logic
        # For now, just accept current response
        state["final_response"] = state.get("generated_response", "Xin lỗi, không thể tạo phản hồi.")
        state["is_final"] = True
        state["should_fallback"] = True
        state["fallback_reason"] = "Quality gate failed after max iterations"

        return state

    # ==========================================================================
    # Flow Control and Quality Gates
    # ==========================================================================

    def _evaluate_quality_gate(
        self,
        state: RAGState,
        iteration: int
    ) -> Dict[str, Any]:
        """
        Evaluate if response passes quality gate.

        Args:
            state: Current RAGState
            iteration: Current iteration number

        Returns:
            Quality gate decision with action
        """
        quality_score = get_quality_score(state)
        threshold = self.config.quality_gate_threshold

        if quality_score >= threshold:
            return {
                "passed": True,
                "score": quality_score,
                "action": "proceed",
                "reasoning": f"Quality score {quality_score:.2f} >= threshold {threshold:.2f}"
            }
        elif iteration >= self.config.max_pipeline_iterations:
            return {
                "passed": False,
                "score": quality_score,
                "action": "accept",
                "reasoning": "Max iterations reached, accepting current response"
            }
        else:
            return {
                "passed": False,
                "score": quality_score,
                "action": "regenerate",
                "reasoning": f"Quality score {quality_score:.2f} < threshold {threshold:.2f}"
            }

    # ==========================================================================
    # Adaptive Routing (TODO)
    # ==========================================================================

    async def _analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """
        Analyze query complexity for adaptive routing.

        TODO: Implement complexity analysis based on:
        - Query length and structure
        - Number of entities/concepts
        - Required reasoning depth

        Args:
            query: User query

        Returns:
            Complexity analysis dict
        """
        # Placeholder
        return {
            "complexity": "medium",
            "reasoning_depth": "shallow",
            "entities_count": 0
        }

    async def _should_skip_agent(self, agent_name: str, state: RAGState) -> bool:
        """
        Decide if an agent should be skipped based on context.

        TODO: Implement adaptive agent skipping based on:
        - Query characteristics
        - Historical patterns
        - Performance metrics

        Args:
            agent_name: Name of agent to evaluate
            state: Current RAGState

        Returns:
            True if agent should be skipped
        """
        # Placeholder - no skipping for now
        return False
