"""
Basic 2-Node LangGraph for Agentic RAG (4-Agent Architecture)

This module implements a simplified 2-node graph for testing the Agentic RAG system:
- Node 1: RetrievalAgent (retrieval + reranking + query expansion)
- Node 2: GenerationAgent (LLM generation with citations)

Graph Structure:
    retrieval → generation → END

This basic graph serves as:
1. Testing ground for agent integration
2. Foundation for more complex graphs
3. Debugging tool for state flow
4. Performance baseline

Example:
    from graphs.basic_2_node_graph_4_agent import create_basic_graph, execute_basic_graph

    # Create graph
    graph = create_basic_graph()

    # Execute
    result = await execute_basic_graph(query="hỏi về hợp đồng", user_id="user123")
    print(result["generated_response"])
"""

import logging
from typing import Dict, Any, Optional, Literal
from uuid import UUID, uuid4
import time

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from models.agentic_rag_state import (
    RAGState,
    AgentResult,
    AgentStatus,
    create_initial_state,
    validate_state,
    create_agent_result,
    mark_agent_start,
    update_state_with_agent_result,
    calculate_total_time,
    update_state_with_error,
    RetrievalAgentConfig,
    GenerationAgentConfig,
    DocumentWithScore
)
from agents.retrieval_agent_4 import RetrievalAgent
from agents.generation_agent_4 import GenerationAgent

logger = logging.getLogger(__name__)


# ============================================================================
# Node Functions
# ============================================================================

async def retrieval_node(state: RAGState) -> Dict[str, Any]:
    """
    Retrieval node: Execute RetrievalAgent with error handling.

    This node:
    1. Executes RetrievalAgent (query refinement + retrieval + reranking)
    2. Tracks execution time
    3. Handles errors gracefully
    4. Updates state with retrieval results

    Args:
        state: Current RAGState

    Returns:
        State update dict
    """
    start_time = time.time()
    logger.info("retrieval_node: Starting retrieval")

    try:
        # Get agent from config (would be injected in production)
        config = state.get("config", {}).get("retrieval", RetrievalAgentConfig())
        llm_client = state.get("llm_client", None)

        # Create agent
        agent = RetrievalAgent(config=config, llm_client=llm_client)

        # Execute retrieval
        updated_state = await agent.handle(state)

        execution_time = (time.time() - start_time) * 1000
        logger.info(f"retrieval_node: Completed in {execution_time:.0f}ms")

        return {
            "retrieval_agent_output": updated_state["retrieval_agent_output"],
            "agent_results": updated_state["agent_results"],
            "current_agent": "retrieval_completed"
        }

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(f"retrieval_node: Failed - {e}", exc_info=True)

        # Add error to state
        error_msg = f"Retrieval failed: {str(e)}"

        return {
            "errors": state.get("errors", []) + [error_msg],
            "should_fallback": True,
            "fallback_reason": error_msg,
            "current_agent": "retrieval_failed"
        }


async def generation_node(state: RAGState) -> Dict[str, Any]:
    """
    Generation node: Execute GenerationAgent with error handling.

    This node:
    1. Checks if retrieval succeeded
    2. Executes GenerationAgent (LLM generation with citations)
    3. Tracks execution time
    4. Handles errors gracefully
    5. Updates state with generated response

    Args:
        state: Current RAGState

    Returns:
        State update dict
    """
    start_time = time.time()
    logger.info("generation_node: Starting generation")

    try:
        # Check if retrieval failed
        if state.get("should_fallback"):
            logger.warning("generation_node: Skipping due to retrieval failure")
            return {
                "generated_response": "Xin lỗi, không thể tìm thấy thông tin liên quan. Vui lòng thử lại.",
                "current_agent": "generation_skipped"
            }

        # Check if we have documents
        retrieval_output = state.get("retrieval_agent_output", {})
        reranked_docs = retrieval_output.get("reranked_docs", [])

        if not reranked_docs:
            logger.warning("generation_node: No documents retrieved")
            return {
                "generated_response": "Không tìm thấy tài liệu liên quan để trả lời câu hỏi này.",
                "current_agent": "generation_no_docs"
            }

        # Get agent from config (would be injected in production)
        config = state.get("config", {}).get("generation", GenerationAgentConfig())
        llm_client = state.get("llm_client")

        if not llm_client:
            raise ValueError("LLM client not found in state")

        # Create agent
        agent = GenerationAgent(config=config, llm_client=llm_client)

        # Execute generation
        updated_state = await agent.handle(state)

        execution_time = (time.time() - start_time) * 1000
        logger.info(f"generation_node: Completed in {execution_time:.0f}ms")

        return {
            "generated_response": updated_state["generated_response"],
            "generation_metadata": updated_state["generation_metadata"],
            "agent_results": updated_state["agent_results"],
            "current_agent": "generation_completed"
        }

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(f"generation_node: Failed - {e}", exc_info=True)

        # Add error to state
        error_msg = f"Generation failed: {str(e)}"

        return {
            "errors": state.get("errors", []) + [error_msg],
            "generated_response": "Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời. Vui lòng thử lại.",
            "current_agent": "generation_failed"
        }


# ============================================================================
# Conditional Edges
# ============================================================================

def should_continue_generation(state: RAGState) -> Literal["generation", END]:
    """
    Decide whether to continue to generation or end.

    Args:
        state: Current RAGState

    Returns:
        "generation" if should continue, END otherwise
    """
    # Check if retrieval failed
    if state.get("should_fallback"):
        logger.info("should_continue: END (retrieval failed)")
        return END

    # Check if we have documents
    retrieval_output = state.get("retrieval_agent_output", {})
    reranked_docs = retrieval_output.get("reranked_docs", [])

    if not reranked_docs:
        logger.info("should_continue: END (no documents)")
        return END

    logger.info("should_continue: generation")
    return "generation"


def should_end(state: RAGState) -> Literal[END]:
    """
    Always end after generation.

    Args:
        state: Current RAGState

    Returns:
        END
    """
    logger.info("should_end: END")
    return END


# ============================================================================
# Graph Creation
# ============================================================================

def create_basic_graph(
    checkpointer: Optional[MemorySaver] = None
) -> StateGraph:
    """
    Create basic 2-node LangGraph for Agentic RAG.

    Graph Structure:
        START → retrieval → generation → END

    Args:
        checkpointer: Optional LangGraph checkpointer for state persistence

    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Creating basic 2-node graph")

    # Create state graph
    builder = StateGraph(RAGState)

    # Add nodes
    builder.add_node("retrieval", retrieval_node)
    builder.add_node("generation", generation_node)

    # Set entry point
    builder.set_entry_point("retrieval")

    # Add conditional edge: retrieval → (generation | END)
    builder.add_conditional_edges(
        "retrieval",
        should_continue_generation,
        {
            "generation": "generation",
            END: END
        }
    )

    # Add edge: generation → END
    builder.add_edge("generation", END)

    # Compile graph
    if checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
    else:
        graph = builder.compile()

    logger.info("Basic graph compiled successfully")
    return graph


# ============================================================================
# Graph Execution
# ============================================================================

async def execute_basic_graph(
    query: str,
    user_id: str,
    conversation_id: Optional[UUID] = None,
    llm_client: Optional[Any] = None,
    retrieval_config: Optional[RetrievalAgentConfig] = None,
    generation_config: Optional[GenerationAgentConfig] = None,
    graph: Optional[StateGraph] = None
) -> RAGState:
    """
    Execute basic 2-node graph with initial state.

    Args:
        query: User query
        user_id: User ID
        conversation_id: Optional conversation ID
        llm_client: LLM client for generation
        retrieval_config: Optional RetrievalAgent config
        generation_config: Optional GenerationAgent config
        graph: Optional pre-created graph (creates new if None)

    Returns:
        Final RAGState after graph execution
    """
    start_time = time.time()
    logger.info(f"execute_basic_graph: query='{query[:50]}...', user={user_id}")

    try:
        # Create initial state
        state = create_initial_state(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id
        )

        # Add config and LLM client to state
        state["config"] = {}
        if retrieval_config:
            state["config"]["retrieval"] = retrieval_config
        if generation_config:
            state["config"]["generation"] = generation_config
        if llm_client:
            state["llm_client"] = llm_client

        # Create graph if not provided
        if graph is None:
            graph = create_basic_graph()

        # Execute graph
        logger.info("execute_basic_graph: Starting graph execution")
        final_state = await graph.ainvoke(state)

        # Calculate total time
        total_time = (time.time() - start_time) * 1000
        final_state = calculate_total_time(final_state)
        final_state["total_execution_time_ms"] = total_time

        # Mark as final
        final_state["is_final"] = True
        final_state["final_response"] = final_state.get("generated_response", "")

        logger.info(f"execute_basic_graph: Completed in {total_time:.0f}ms")

        return final_state

    except Exception as e:
        logger.error(f"execute_basic_graph: Failed - {e}", exc_info=True)

        # Return error state
        error_state = create_initial_state(query, user_id, conversation_id)
        error_state["errors"].append(f"Graph execution failed: {str(e)}")
        error_state["should_fallback"] = True
        error_state["fallback_reason"] = str(e)
        error_state["is_final"] = True

        return error_state


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_state(
    query: str = "test query",
    user_id: str = "test_user",
    include_documents: bool = True
) -> RAGState:
    """
    Create test state for unit testing.

    Args:
        query: Test query
        user_id: Test user ID
        include_documents: Whether to include mock documents

    Returns:
        Test RAGState
    """
    state = create_initial_state(query=query, user_id=user_id)

    if include_documents:
        # Add mock documents
        mock_docs = [
            DocumentWithScore(
                doc_id=uuid4(),
                content="Test document content about the query",
                filename="test.pdf",
                page_number=1,
                chunk_index=0,
                score=0.85,
                metadata={"test": True}
            ).model_dump()
        ]

        state["retrieval_agent_output"]["reranked_docs"] = mock_docs
        state["retrieval_agent_output"]["retrieved_docs"] = mock_docs

    return state


async def execute_graph_with_streaming(
    query: str,
    user_id: str,
    llm_client: Any,
    conversation_id: Optional[UUID] = None,
    graph: Optional[StateGraph] = None
):
    """
    Execute graph with streaming updates.

    Yields state updates as nodes complete.

    Args:
        query: User query
        user_id: User ID
        llm_client: LLM client
        conversation_id: Optional conversation ID
        graph: Optional pre-created graph

    Yields:
        Streaming updates during execution
    """
    logger.info(f"execute_graph_with_streaming: Starting")

    # Create initial state
    state = create_initial_state(query=query, user_id=user_id, conversation_id=conversation_id)
    state["llm_client"] = llm_client

    # Create graph if not provided
    if graph is None:
        graph = create_basic_graph()

    # Execute with streaming
    async for event in graph.astream(state):
        yield event


# ============================================================================
# Visualization
# ============================================================================

def print_graph_structure() -> None:
    """Print graph structure for debugging."""
    print("\n" + "="*60)
    print("Basic 2-Node Agentic RAG Graph Structure")
    print("="*60)
    print("\nNodes:")
    print("  1. retrieval  - RetrievalAgent (query refinement + retrieval + reranking)")
    print("  2. generation - GenerationAgent (LLM generation with citations)")
    print("\nEdges:")
    print("  START → retrieval → generation → END")
    print("\nConditional Flow:")
    print("  - If retrieval succeeds with documents → generation")
    print("  - If retrieval fails or no documents → END")
    print("\n" + "="*60 + "\n")


# ============================================================================
# Main Execution Example
# ============================================================================

async def main():
    """
    Example execution of basic graph.

    This demonstrates how to use the basic graph for testing.
    """
    print_graph_structure()

    # Mock LLM client (in production, use actual LLMClient)
    class MockLLMClient:
        async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
            return "Đây là câu trả lời mẫu từ hệ thống RAG. Trong thực tế, đây sẽ là câu trả lời được tạo bởi LLM dựa trên context."

    # Create state
    query = "Hỏi về điều khoản trong hợp đồng lao động"
    user_id = "user123"

    # Execute graph
    result = await execute_basic_graph(
        query=query,
        user_id=user_id,
        llm_client=MockLLMClient()
    )

    # Print results
    print("\n" + "="*60)
    print("Graph Execution Results")
    print("="*60)
    print(f"\nQuery: {query}")
    print(f"Response: {result['generated_response']}")
    print(f"\nExecution Time: {result.get('total_execution_time_ms', 0):.0f}ms")
    print(f"Errors: {len(result.get('errors', []))}")
    print(f"Agent Results: {len(result.get('agent_results', []))}")
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
