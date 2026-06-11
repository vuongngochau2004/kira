"""
Usage Examples for Agentic RAG System (4-Agent Architecture)

This module demonstrates how to use the Agentic RAG system
with the new 4-agent architecture.

4-AGENT ARCHITECTURE:
1. OrchestratorAgent - Coordination and routing
2. RetrievalAgent - Query refinement + retrieval + reranking (merged)
3. GenerationAgent - LLM generation with citations
4. QualityAgent - Critique + verification (merged)
"""

import asyncio
import logging
from uuid import uuid4

from src.agents.llm import LLMClient
from src.agentic_rag.schemas import (
    AgenticRAGConfig,
    OrchestratorAgentConfig,
    RetrievalAgentConfig,
    GenerationAgentConfig,
    QualityAgentConfig
)
from src.agentic_rag.graph.agentic_rag_graph import create_agentic_rag_graph
from src.agentic_rag.integration.agentic_rag_handler import (
    create_agentic_rag_handler,
    create_agentic_rag_adapter
)
from src.agentic_rag.integration.feature_flags import (
    create_agentic_rag_feature_flags,
    AgenticRAGRolloutStrategy,
    create_agentic_rag_rollout_strategy
)
from src.interfaces.classification import ClassificationResult, Intent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Basic Usage (4-Agent Architecture)
# ============================================================================

async def example_basic_usage():
    """Example: Basic Agentic RAG usage with 4-agent architecture"""

    print("\n" + "="*60)
    print("Example 1: Basic Agentic RAG Usage (4-Agent Architecture)")
    print("="*60)

    # Create LLM client
    llm_client = LLMClient()

    # Create Agentic RAG configuration (4-agent architecture)
    config = AgenticRAGConfig(
        enable_fallback=True,
        orchestrator=OrchestratorAgentConfig(
            enable_routing=True,
            quality_gate_threshold=0.7
        ),
        retrieval=RetrievalAgentConfig(
            top_k=10,
            expansion_count=3,
            enable_reranking=True,
            rerank_top_k=5
        ),
        generation=GenerationAgentConfig(
            model="glm-4.5",
            temperature=0.7
        ),
        quality=QualityAgentConfig(
            quality_threshold=0.7,
            verification_threshold=0.8
        )
    )

    # Create graph
    graph = create_agentic_rag_graph(
        config=config,
        llm_client=llm_client
    )

    # Execute query
    query = "Điều khoản chấm dứt hợp đồng được quy định như thế nào?"
    user_id = "user-123"

    print(f"\nQuery: {query}")
    print(f"User: {user_id}")

    state = await graph.execute(
        query=query,
        user_id=user_id
    )

    print(f"\nResponse: {state.get('final_response', 'No response')}")
    print(f"Citations: {len(state.get('final_citations', []))}")
    print(f"Execution time: {state.get('total_execution_time_ms', 0):.2f}ms")
    print(f"Agents executed: {len(state.get('agent_results', []))}")

    for agent_result in state.get('agent_results', []):
        print(f"  - {agent_result.agent_name}: {agent_result.status.value} ({agent_result.execution_time_ms:.2f}ms)")


# ============================================================================
# Example 2: Streaming Response
# ============================================================================

async def example_streaming_response():
    """Example: Streaming response"""

    print("\n" + "="*60)
    print("Example 2: Streaming Response")
    print("="*60)

    llm_client = LLMClient()
    config = AgenticRAGConfig()

    graph = create_agentic_rag_graph(
        config=config,
        llm_client=llm_client
    )

    query = "Tìm hiểu về quy định báo cáo tài chính"
    user_id = "user-456"

    print(f"\nQuery: {query}")
    print(f"\nStreaming response:")

    async for chunk in graph.execute_stream(
        query=query,
        user_id=user_id
    ):
        chunk_type = chunk.get("type")
        chunk_data = chunk.get("data", {})

        if chunk_type == "agent_progress":
            print(f"\n[Agent: {chunk_data.get('agent')}]")

        elif chunk_type == "content":
            print(chunk_data.get("text", ""), end="", flush=True)

        elif chunk_type == "metadata":
            print(f"\n\nCitations: {len(chunk_data.get('citations', []))}")

        elif chunk_type == "error":
            print(f"\nError: {chunk_data.get('message')}")

        elif chunk_type == "done":
            print(f"\n\nCompleted in {chunk_data.get('execution_time_ms', 0):.2f}ms")


# ============================================================================
# Example 3: Handler Integration
# ============================================================================

async def example_handler_integration():
    """Example: Using AgenticRAGHandler"""

    print("\n" + "="*60)
    print("Example 3: Handler Integration")
    print("="*60)

    llm_client = LLMClient()
    config = AgenticRAGConfig()

    # Create handler
    handler = create_agentic_rag_handler(
        llm_client=llm_client,
        agentic_config=config
    )

    # Create classification
    classification = ClassificationResult(
        intent=Intent.RAG,
        confidence=0.95,
        metadata={"strategy": "keyword"}
    )

    query = "Quy trình phê duyệt ngân sách như thế nào?"
    user_id = "user-789"

    print(f"\nQuery: {query}")

    # Handle query
    result = await handler.handle(
        query=query,
        user_id=user_id,
        classification=classification
    )

    print(f"\nResponse: {result.content[:200]}...")
    print(f"Citations: {len(result.citations)}")
    print(f"Metadata: {result.metadata}")


# ============================================================================
# Example 4: Feature Flags
# ============================================================================

async def example_feature_flags():
    """Example: Using feature flags"""

    print("\n" + "="*60)
    print("Example 4: Feature Flags")
    print("="*60)

    # Create feature flags
    feature_flags = create_agentic_rag_feature_flags()

    # Check rollout status
    status = feature_flags.get_rollout_status()
    print(f"\nCurrent rollout status:")
    for flag, percentage in status.items():
        print(f"  {flag}: {percentage}%")

    # Check if enabled for specific users
    users = ["user-1", "user-2", "user-3", "user-4", "user-5"]

    print(f"\nAgentic RAG enabled for users:")
    for user_id in users:
        enabled = feature_flags.is_agentic_rag_enabled(user_id)
        print(f"  {user_id}: {'Yes' if enabled else 'No'}")

    # Get config for specific user
    user_config = feature_flags.get_config_for_user("user-1")
    print(f"\nConfig for user-1:")
    print(f"  Query refinement: {user_config.enable_query_refinement}")
    print(f"  Reranking: {user_config.enable_reranking}")
    print(f"  Critique: {user_config.enable_critique}")
    print(f"  Verification: {user_config.enable_verification}")


# ============================================================================
# Example 5: Rollout Strategy
# ============================================================================

async def example_rollout_strategy():
    """Example: Rollout strategy"""

    print("\n" + "="*60)
    print("Example 5: Rollout Strategy")
    print("="*60)

    # Create rollout strategy
    rollout = create_agentic_rag_rollout_strategy()

    print(f"\nCurrent phase: {rollout.get_current_phase()}")

    # Simulate phased rollout
    print("\nSimulating phased rollout:")

    print("\nPhase 1: Internal testing")
    rollout.rollout_phase_1()
    print(f"  Current phase: {rollout.get_current_phase()}")

    print("\nPhase 2: Beta rollout (5%)")
    rollout.rollout_phase_2(percentage=5)
    print(f"  Current phase: {rollout.get_current_phase()}")

    print("\nPhase 3: Gradual rollout (25%)")
    rollout.rollout_phase_3(percentage=25)
    print(f"  Current phase: {rollout.get_current_phase()}")

    print("\nPhase 4: Full rollout (100%)")
    rollout.rollout_phase_4()
    print(f"  Current phase: {rollout.get_current_phase()}")


# ============================================================================
# Example 6: Custom Configuration
# ============================================================================

async def example_custom_configuration():
    """Example: Custom configuration"""

    print("\n" + "="*60)
    print("Example 6: Custom Configuration")
    print("="*60)

    # Create custom configuration
    config = AgenticRAGConfig(
        # Global settings
        enable_fallback=True,
        fallback_timeout_ms=30000,
        max_total_time_ms=45000,

        # Query refiner
        enable_query_refinement=True,
        query_refiner_expansion_count=5,
        query_refiner_use_llm_expansion=True,
        query_refiner_use_synonym_expansion=True,

        # Retrieval
        retrieval_top_k=15,
        retrieval_use_expansion=True,
        retrieval_strategies=["hybrid"],
        retrieval_min_score_threshold=0.4,

        # Reranking
        enable_reranking=True,
        reranking_top_k=7,
        reranking_score_threshold=0.6,

        # Generation
        generation_model="glm-4.5",
        generation_temperature=0.8,
        generation_max_tokens=2500,
        generation_stream_response=True,

        # Critique
        enable_critique=True,
        critique_quality_threshold=0.75,
        critique_max_iterations=3,

        # Verification
        enable_verification=True,
        verification_verification_threshold=0.85,
        verification_max_iterations=2,
        verification_verify_facts=True,
        verification_verify_citations=True,

        # Logging
        log_agent_execution=True,
        log_intermediate_results=False
    )

    print("\nCustom configuration:")
    print(f"  Query refinement: {config.enable_query_refinement}")
    print(f"  Reranking: {config.enable_reranking}")
    print(f"  Critique: {config.enable_critique}")
    print(f"  Verification: {config.enable_verification}")
    print(f"  Fallback timeout: {config.fallback_timeout_ms}ms")
    print(f"  Max total time: {config.max_total_time_ms}ms")


# ============================================================================
# Example 7: Error Handling
# ============================================================================

async def example_error_handling():
    """Example: Error handling and fallback"""

    print("\n" + "="*60)
    print("Example 7: Error Handling")
    print("="*60)

    llm_client = LLMClient()

    # Configuration with fallback enabled
    config = AgenticRAGConfig(
        enable_fallback=True,
        fallback_timeout_ms=30000
    )

    handler = create_agentic_rag_handler(
        llm_client=llm_client,
        agentic_config=config
    )

    classification = ClassificationResult(
        intent=Intent.RAG,
        confidence=0.9,
        metadata={}
    )

    query = "Query that might cause issues"
    user_id = "user-error-test"

    print(f"\nQuery: {query}")

    try:
        result = await handler.handle(
            query=query,
            user_id=user_id,
            classification=classification
        )

        print(f"\nResponse received: {result.content[:100]}...")
        print(f"Handler: {result.metadata.get('handler')}")

        # Check if fallback occurred
        if result.metadata.get('fallback_used'):
            print("Note: Fallback to simple RAG was used")

    except Exception as e:
        print(f"\nError occurred: {e}")
        print("System handled error gracefully")


# ============================================================================
# Example 8: Performance Monitoring
# ============================================================================

async def example_performance_monitoring():
    """Example: Performance monitoring"""

    print("\n" + "="*60)
    print("Example 8: Performance Monitoring")
    print("="*60)

    llm_client = LLMClient()
    config = AgenticRAGConfig(
        log_agent_execution=True
    )

    graph = create_agentic_rag_graph(
        config=config,
        llm_client=llm_client
    )

    query = "Performance test query"
    user_id = "user-perf-test"

    print(f"\nQuery: {query}")

    state = await graph.execute(
        query=query,
        user_id=user_id
    )

    print(f"\nPerformance Summary:")
    print(f"Total execution time: {state.get('total_execution_time_ms', 0):.2f}ms")

    print(f"\nAgent Performance:")
    for agent_result in state.get('agent_results', []):
        print(f"  {agent_result.agent_name}:")
        print(f"    Status: {agent_result.status.value}")
        print(f"    Time: {agent_result.execution_time_ms:.2f}ms")
        if agent_result.metadata:
            print(f"    Metadata: {agent_result.metadata}")


# ============================================================================
# Main Runner
# ============================================================================

async def main():
    """Run all examples"""

    print("\n" + "="*60)
    print("Agentic RAG System - Usage Examples")
    print("="*60)

    examples = [
        ("Basic Usage", example_basic_usage),
        ("Streaming Response", example_streaming_response),
        ("Handler Integration", example_handler_integration),
        ("Feature Flags", example_feature_flags),
        ("Rollout Strategy", example_rollout_strategy),
        ("Custom Configuration", example_custom_configuration),
        ("Error Handling", example_error_handling),
        ("Performance Monitoring", example_performance_monitoring)
    ]

    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            logger.error(f"Example '{name}' failed: {e}", exc_info=True)

        print("\n" + "="*60)

    print("\nAll examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
