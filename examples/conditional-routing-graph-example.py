"""
Conditional Routing Graph Example - 3-Node with Dynamic Routing

This example demonstrates conditional routing based on state:
1. Analyzer Node: Classify query type
2. Short Processor: Process short queries (uppercase)
3. Long Processor: Process long queries (add prefix)

Conditional routing logic:
- Query length ≤ 10 → short_processor
- Query length > 10 → long_processor

Learning objectives:
- Conditional edge implementation
- Routing function design
- Multiple execution paths
- Dynamic state-based routing
"""

from typing import TypedDict, Literal
from enum import Enum
import time
from langgraph.graph import StateGraph, END


# ============================================================================
# Enum Definitions
# ============================================================================

class QueryType(Enum):
    """Query type classification"""
    SHORT = "short"
    LONG = "long"


# ============================================================================
# State Definition
# ============================================================================

class ConditionalState(TypedDict):
    """State for conditional routing graph"""
    query: str                  # Input: user query
    query_type: QueryType       # Classification result
    result: str                 # Output: processed result
    processing_time_ms: float   # Metrics: processing time


# ============================================================================
# Node Functions
# ============================================================================

def analyzer_node(state: ConditionalState) -> dict:
    """Analyze query and classify as SHORT or LONG"""

    query = state["query"]
    query_type = QueryType.SHORT if len(query) <= 10 else QueryType.LONG

    print(f"\n[Analyzer]")
    print(f"  Query: '{query}'")
    print(f"  Length: {len(query)} characters")
    print(f"  Type: {query_type.value}")

    return {"query_type": query_type}


def short_processor_node(state: ConditionalState) -> dict:
    """Process short queries (convert to uppercase)"""

    query = state["query"]
    start_time = time.time()

    result = query.upper()
    processing_time = (time.time() - start_time) * 1000

    print(f"\n[Short Processor]")
    print(f"  Input: '{query}'")
    print(f"  Output: '{result}'")
    print(f"  Time: {processing_time:.2f}ms")

    return {
        "result": result,
        "processing_time_ms": processing_time
    }


def long_processor_node(state: ConditionalState) -> dict:
    """Process long queries (add prefix)"""

    query = state["query"]
    start_time = time.time()

    result = f"[LONG QUERY]: {query}"
    processing_time = (time.time() - start_time) * 1000

    print(f"\n[Long Processor]")
    print(f"  Input: '{query}'")
    print(f"  Output: '{result}'")
    print(f"  Time: {processing_time:.2f}ms")

    return {
        "result": result,
        "processing_time_ms": processing_time
    }


# ============================================================================
# Routing Function
# ============================================================================

def route_by_length(state: ConditionalState) -> Literal["short_processor", "long_processor"]:
    """Route to appropriate processor based on query type"""

    query_type = state["query_type"]

    print(f"\n[Router]")
    print(f"  Routing decision: {query_type.value}_processor")

    if query_type == QueryType.SHORT:
        return "short_processor"
    else:
        return "long_processor"


# ============================================================================
# Graph Construction
# ============================================================================

def create_conditional_graph() -> StateGraph:
    """Create graph with conditional routing"""

    # Initialize graph
    graph = StateGraph(ConditionalState)

    # Add nodes
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("short_processor", short_processor_node)
    graph.add_node("long_processor", long_processor_node)

    # Set entry point
    graph.set_entry_point("analyzer")

    # Add conditional edge from analyzer
    graph.add_conditional_edges(
        "analyzer",
        route_by_length,
        {
            "short_processor": "short_processor",
            "long_processor": "long_processor"
        }
    )

    # Add edges to END
    graph.add_edge("short_processor", END)
    graph.add_edge("long_processor", END)

    # Compile graph
    return graph.compile()


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Execute conditional routing graph"""

    print("\n" + "="*60)
    print("Conditional Routing Graph Example")
    print("="*60)
    print("\nThis graph routes queries based on their length:")
    print("  • ≤ 10 characters → Short Processor (uppercase)")
    print("  • > 10 characters → Long Processor (add prefix)")

    # Create graph
    app = create_conditional_graph()

    # Test queries
    test_queries = [
        "Hi",                    # SHORT (2 chars)
        "Hello",                 # SHORT (5 chars)
        "Hello World",           # LONG (11 chars)
        "This is a very long query",  # LONG (26 chars)
        "Test",                  # SHORT (4 chars)
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Testing Query: '{query}' ({len(query)} chars)")
        print('='*60)

        # Execute graph
        result = app.invoke({
            "query": query,
            "processing_time_ms": 0.0
        })

        # Display result
        print(f"\n{'─'*60}")
        print("Result Summary:")
        print('─'*60)
        print(f"  Query:    {result['query']}")
        print(f"  Type:     {result['query_type'].value}")
        print(f"  Result:   {result['result']}")
        print(f"  Time:     {result['processing_time_ms']:.2f}ms")

    print("\n" + "="*60)
    print("Example Complete!")
    print("="*60 + "\n")


# ============================================================================
# Module Information
# ============================================================================

if __name__ == "__main__":
    main()

__doc__ = """
Conditional Routing Graph Example

Demonstrates:
- Conditional edge implementation
- State-based routing decisions
- Multiple execution paths
- Routing function design

Run: python examples/conditional-routing-graph-example.py
"""

__all__ = [
    "QueryType",
    "ConditionalState",
    "analyzer_node",
    "short_processor_node",
    "long_processor_node",
    "route_by_length",
    "create_conditional_graph"
]
