"""
Error Handling Graph Example - Graceful Degradation

This example demonstrates error handling and fallback mechanisms:
1. Safe Processor: Process with error handling
2. Fallback Handler: Fallback logic for errors
3. Error Router: Decide whether to retry or fallback

Learning objectives:
- Node-level error handling
- Graph-level fallback mechanisms
- Retry logic with counters
- Graceful degradation patterns
"""

from typing import TypedDict, Literal
import random
import logging
from langgraph.graph import StateGraph, END


# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# State Definition
# ============================================================================

class ErrorHandlingState(TypedDict):
    """State for error handling graph"""
    query: str              # Input: user query
    result: str             # Output: processing result
    success: bool           # Status: operation success
    retry_count: int        # Counter: retry attempts
    max_retries: int        # Config: maximum retries allowed
    errors: list[str]       # Accumulated errors


# ============================================================================
# Node Functions
# ============================================================================

def safe_processor_node(state: ErrorHandlingState) -> dict:
    """Processor with simulated failures (50% failure rate)"""

    query = state["query"]
    retry_count = state["retry_count"]

    print(f"\n[Safe Processor] (Attempt {retry_count + 1})")
    print(f"  Processing: '{query}'")

    # Simulate 50% failure rate
    if random.random() < 0.5:
        error_msg = f"Random failure on attempt {retry_count + 1}"
        print(f"  ❌ Failed: {error_msg}")

        return {
            "success": False,
            "errors": state.get("errors", []) + [error_msg]
        }
    else:
        result = f"SUCCESS: {query.upper()}"
        print(f"  ✅ Success: {result}")

        return {
            "result": result,
            "success": True
        }


def fallback_handler_node(state: ErrorHandlingState) -> dict:
    """Fallback handler when all retries exhausted"""

    query = state["query"]
    errors = state.get("errors", [])

    print(f"\n[Fallback Handler]")
    print(f"  Query: '{query}'")
    print(f"  Errors: {len(errors)}")

    # Provide fallback response
    result = f"[FALLBACK] Could not process '{query}' after {state['retry_count']} attempts"

    print(f"  Result: {result}")

    return {
        "result": result,
        "success": True  # Fallback always succeeds
    }


def retry_counter_node(state: ErrorHandlingState) -> dict:
    """Increment retry counter"""

    retry_count = state["retry_count"] + 1

    print(f"\n[Retry Counter]")
    print(f"  Previous count: {state['retry_count']}")
    print(f"  New count: {retry_count}")

    return {"retry_count": retry_count}


# ============================================================================
# Routing Functions
# ============================================================================

def error_handling_router(state: ErrorHandlingState) -> Literal["retry", "fallback", "end"]:
    """Decide whether to retry, fallback, or end"""

    success = state.get("success", False)
    retry_count = state["retry_count"]
    max_retries = state["max_retries"]

    print(f"\n[Error Router]")
    print(f"  Success: {success}")
    print(f"  Retries: {retry_count}/{max_retries}")

    # Success → end
    if success:
        print("  Decision: END (success)")
        return "end"

    # Under max retries → retry
    if retry_count < max_retries:
        print("  Decision: RETRY")
        return "retry"

    # Max retries exhausted → fallback
    print("  Decision: FALLBACK (max retries reached)")
    return "fallback"


# ============================================================================
# Graph Construction
# ============================================================================

def create_error_handling_graph(max_retries: int = 3) -> StateGraph:
    """Create graph with error handling"""

    # Initialize graph
    graph = StateGraph(ErrorHandlingState)

    # Add nodes
    graph.add_node("safe_processor", safe_processor_node)
    graph.add_node("retry_counter", retry_counter_node)
    graph.add_node("fallback_handler", fallback_handler_node)

    # Set entry point
    graph.set_entry_point("safe_processor")

    # Add conditional edge from safe_processor
    graph.add_conditional_edges(
        "safe_processor",
        error_handling_router,
        {
            "retry": "retry_counter",
            "fallback": "fallback_handler",
            "end": END
        }
    )

    # Add edge back to processor after retry counter
    graph.add_edge("retry_counter", "safe_processor")

    # Add edge to END after fallback
    graph.add_edge("fallback_handler", END)

    # Compile graph
    return graph.compile()


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Execute error handling graph"""

    print("\n" + "="*60)
    print("Error Handling Graph Example")
    print("="*60)
    print("\nThis graph demonstrates:")
    print("  • 50% random failure rate")
    print("  • Retry logic (max 3 attempts)")
    print("  • Fallback handler")
    print("  • Graceful degradation")

    # Create graph
    app = create_error_handling_graph(max_retries=3)

    # Test queries
    test_queries = [
        "test-query-1",
        "test-query-2",
        "test-query-3",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}: '{query}'")
        print('='*60)

        # Execute graph
        result = app.invoke({
            "query": query,
            "success": False,
            "retry_count": 1,
            "max_retries": 3,
            "errors": []
        })

        # Display result
        print(f"\n{'─'*60}")
        print("Result Summary:")
        print('─'*60)
        print(f"  Query:       {result['query']}")
        print(f"  Result:      {result['result']}")
        print(f"  Success:     {result['success']}")
        print(f"  Retries:     {result['retry_count']}")
        print(f"  Errors:      {len(result['errors'])}")

    print("\n" + "="*60)
    print("Example Complete!")
    print("="*60 + "\n")


# ============================================================================
# Module Information
# ============================================================================

if __name__ == "__main__":
    main()

__doc__ = """
Error Handling Graph Example

Demonstrates:
- Node-level error handling with try/except
- Graph-level fallback mechanisms
- Retry logic with exponential backoff potential
- Graceful degradation patterns

Run: python examples/error-handling-graph-example.py
"""

__all__ = [
    "ErrorHandlingState",
    "safe_processor_node",
    "fallback_handler_node",
    "retry_counter_node",
    "error_handling_router",
    "create_error_handling_graph"
]
