"""
Streaming Graph Example - Real-time Token Streaming

This example demonstrates streaming support in LangGraph:
- Real-time progress updates
- Token-by-token streaming
- Agent execution events
- Structured chunk streaming

Learning objectives:
- Implement streaming in nodes
- Stream graph execution
- Handle different chunk types
- Real-time progress reporting
"""

from typing import TypedDict, AsyncIterator, Dict, Any
import asyncio
import time
from langgraph.graph import StateGraph, END


# ============================================================================
# State Definition
# ============================================================================

class StreamingState(TypedDict):
    """State for streaming graph"""
    query: str              # Input: user query
    result: str             # Output: accumulated result
    progress: float         # Progress percentage
    current_agent: str      # Current executing agent


# ============================================================================
# Streaming Node Functions
# ============================================================================

async def streaming_retrieval_node(state: StreamingState) -> AsyncIterator[Dict[str, Any]]:
    """Retrieval node with streaming updates"""

    query = state["query"]

    # Emit start event
    yield {
        "type": "agent_start",
        "data": {
            "agent": "retrieval",
            "query": query
        }
    }

    # Simulate document retrieval
    print(f"\n[Retrieval] Searching for: {query}")
    docs = ["doc1", "doc2", "doc3"]

    # Stream each document
    for i, doc in enumerate(docs):
        await asyncio.sleep(0.5)  # Simulate retrieval time

        yield {
            "type": "agent_progress",
            "data": {
                "agent": "retrieval",
                "status": f"Retrieved {i+1}/{len(docs)} documents",
                "progress": (i+1) / len(docs) * 100
            }
        }

    # Emit complete event
    yield {
        "type": "agent_complete",
        "data": {
            "agent": "retrieval",
            "doc_count": len(docs),
            "time_ms": 1500
        }
    }

    # Return state update
    yield {
        "type": "state_update",
        "data": {
            "progress": 33.3,
            "current_agent": "retrieval"
        }
    }


async def streaming_generation_node(state: StreamingState) -> AsyncIterator[Dict[str, Any]]:
    """Generation node with token streaming"""

    query = state["query"]

    # Emit start event
    yield {
        "type": "agent_start",
        "data": {
            "agent": "generation",
            "query": query
        }
    }

    # Simulate token generation
    tokens = ["This", " is", " a", " streaming", " response", " for:", f" '{query}'"]

    print(f"\n[Generation] Streaming tokens...")

    for token in tokens:
        await asyncio.sleep(0.3)  # Simulate generation time

        yield {
            "type": "token",
            "data": {
                "token": token,
                "agent": "generation"
            }
        }

    # Emit complete event
    yield {
        "type": "agent_complete",
        "data": {
            "agent": "generation",
            "token_count": len(tokens),
            "time_ms": 1800
        }
    }

    # Build result
    result = " ".join(tokens)

    # Return state update
    yield {
        "type": "state_update",
        "data": {
            "result": result,
            "progress": 100.0,
            "current_agent": "generation"
        }
    }


async def streaming_critique_node(state: StreamingState) -> AsyncIterator[Dict[str, Any]]:
    """Critique node with quality streaming"""

    result = state.get("result", "")

    # Emit start event
    yield {
        "type": "agent_start",
        "data": {
            "agent": "critique",
            "result_length": len(result)
        }
    }

    # Simulate quality checks
    checks = ["grammar", "coherence", "citation"]

    print(f"\n[Critique] Running quality checks...")

    for i, check in enumerate(checks):
        await asyncio.sleep(0.4)  # Simulate check time

        yield {
            "type": "critique_progress",
            "data": {
                "check": check,
                "status": "passed",
                "progress": (i+1) / len(checks) * 100
            }
        }

    # Calculate quality score
    quality_score = 0.92

    # Emit complete event
    yield {
        "type": "agent_complete",
        "data": {
            "agent": "critique",
            "quality_score": quality_score,
            "checks_passed": len(checks),
            "time_ms": 1200
        }
    }

    # Return state update
    yield {
        "type": "state_update",
        "data": {
            "current_agent": "critique"
        }
    }


# ============================================================================
# Graph Construction (Simplified - nodes return state updates)
# ============================================================================

def create_streaming_graph():
    """Create streaming-capable graph

    Note: For true streaming, use custom execution logic
    that handles AsyncIterator nodes
    """

    # This is a simplified version
    # Full streaming requires custom graph execution
    print("Streaming graph requires custom execution logic")
    print("See main() for streaming implementation")


# ============================================================================
# Streaming Execution
# ============================================================================

async def execute_streaming_graph(query: str):
    """Execute graph with streaming"""

    print("\n" + "="*60)
    print("Streaming Graph Execution")
    print("="*60)
    print(f"\nQuery: {query}")

    state = {
        "query": query,
        "result": "",
        "progress": 0.0,
        "current_agent": ""
    }

    total_time = 0

    # Execute retrieval
    print("\n" + "─"*60)
    print("Phase 1: Retrieval")
    print('─'*60)

    start_time = time.time()
    async for chunk in streaming_retrieval_node(state):
        await handle_stream_chunk(chunk)
    retrieval_time = (time.time() - start_time) * 1000

    # Execute generation
    print("\n" + "─"*60)
    print("Phase 2: Generation")
    print('─'*60)

    start_time = time.time()
    async for chunk in streaming_generation_node(state):
        await handle_stream_chunk(chunk)
    generation_time = (time.time() - start_time) * 1000

    # Execute critique
    print("\n" + "─"*60)
    print("Phase 3: Critique")
    print('─'*60)

    start_time = time.time()
    async for chunk in streaming_critique_node(state):
        await handle_stream_chunk(chunk)
    critique_time = (time.time() - start_time) * 1000

    total_time = retrieval_time + generation_time + critique_time

    # Emit final done event
    print("\n" + "="*60)
    print("Execution Complete")
    print("="*60)
    print(f"Total time: {total_time:.0f}ms")
    print(f"Result: {state.get('result', '')}")


async def handle_stream_chunk(chunk: Dict[str, Any]):
    """Handle streaming chunk"""

    chunk_type = chunk.get("type")
    chunk_data = chunk.get("data", {})

    if chunk_type == "agent_start":
        print(f"\n▶ [{chunk_data['agent'].title()}] Starting...")

    elif chunk_type == "agent_progress":
        status = chunk_data.get("status", "")
        progress = chunk_data.get("progress", 0)
        print(f"  Progress: {status} ({progress:.0f}%)")

    elif chunk_type == "token":
        print(chunk_data["token"], end=" ", flush=True)

    elif chunk_type == "critique_progress":
        check = chunk_data["check"]
        print(f"  ✓ {check.title()} check: PASSED")

    elif chunk_type == "agent_complete":
        agent = chunk_data["agent"].title()
        time_ms = chunk_data.get("time_ms", 0)
        print(f"\n✓ [{agent}] Complete ({time_ms:.0f}ms)")

    elif chunk_type == "state_update":
        # Handle state updates
        pass


# ============================================================================
# Main Execution
# ============================================================================

async def main():
    """Execute streaming examples"""

    print("\n" + "="*60)
    print("Streaming Graph Example")
    print("="*60)
    print("\nThis example demonstrates:")
    print("  • Real-time agent progress updates")
    print("  • Token-by-token streaming")
    print("  • Quality check streaming")
    print("  • Structured chunk handling")

    # Test queries
    test_queries = [
        "What is LangGraph?",
        "Explain RAG architecture"
    ]

    for query in test_queries:
        await execute_streaming_graph(query)

        print("\n" + "="*60 + "\n")

    print("All examples complete!")


# ============================================================================
# Module Information
# ============================================================================

if __name__ == "__main__":
    asyncio.run(main())

__doc__ = """
Streaming Graph Example

Demonstrates:
- AsyncIterator for node streaming
- Real-time progress updates
- Token-by-token streaming
- Agent execution events
- Structured chunk handling

Run: python examples/streaming-graph-example.py
"""

__all__ = [
    "StreamingState",
    "streaming_retrieval_node",
    "streaming_generation_node",
    "streaming_critique_node",
    "execute_streaming_graph"
]
