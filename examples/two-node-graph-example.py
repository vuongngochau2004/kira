"""
Two-Node Graph Example - Processor and Formatter

This example demonstrates a simple 2-node pipeline:
1. Processor Node: Add prefix to input
2. Formatter Node: Add timestamp to output

Learning objectives:
- Multi-node graph construction
- Sequential node execution
- State flow between nodes
"""

from typing import TypedDict
from datetime import datetime
from langgraph.graph import StateGraph, END


# ============================================================================
# State Definition
# ============================================================================

class TwoNodeState(TypedDict):
    """State for 2-node graph"""
    query: str              # Input: user query
    processed: str          # Intermediate: processed query
    timestamp: str          # Output: final formatted output


# ============================================================================
# Node Functions
# ============================================================================

def processor_node(state: TwoNodeState) -> dict:
    """Process query: add PROCESSED prefix"""

    query = state["query"]
    processed = f"PROCESSED:{query}"

    print(f"\n[Processor]")
    print(f"  Input:  {query}")
    print(f"  Output: {processed}")

    return {"processed": processed}


def formatter_node(state: TwoNodeState) -> dict:
    """Format output: add timestamp"""

    processed = state["processed"]
    timestamp = datetime.now().isoformat()

    output = f"{processed} | {timestamp}"

    print(f"\n[Formatter]")
    print(f"  Input:  {processed}")
    print(f"  Output: {output}")

    return {"timestamp": output}


# ============================================================================
# Graph Construction
# ============================================================================

def create_two_node_graph() -> StateGraph:
    """Create 2-node graph"""

    # Initialize graph
    graph = StateGraph(TwoNodeState)

    # Add nodes
    graph.add_node("processor", processor_node)
    graph.add_node("formatter", formatter_node)

    # Set entry point
    graph.set_entry_point("processor")

    # Add edges (linear flow)
    graph.add_edge("processor", "formatter")
    graph.add_edge("formatter", END)

    # Compile graph
    return graph.compile()


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Execute 2-node graph"""

    print("\n" + "="*60)
    print("Two-Node Graph Example")
    print("="*60)

    # Create graph
    app = create_two_node_graph()

    # Test queries
    test_queries = [
        "Hello LangGraph!",
        "This is a test",
        "Multi-node pipeline example"
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)

        # Execute graph
        result = app.invoke({"query": query})

        # Display result
        print(f"\n{'─'*60}")
        print("Final Result:")
        print('─'*60)
        print(f"  Original Query: {result['query']}")
        print(f"  Processed:      {result['processed']}")
        print(f"  Final Output:   {result['timestamp']}")

    print("\n" + "="*60)
    print("Example Complete!")
    print("="*60 + "\n")


# ============================================================================
# Module Information
# ============================================================================

if __name__ == "__main__":
    main()

__doc__ = """
Two-Node Graph Example

Demonstrates:
- Multi-node graph construction
- Sequential execution (processor → formatter → END)
- State updates between nodes
- Linear pipeline pattern

Run: python examples/two-node-graph-example.py
"""

__all__ = [
    "TwoNodeState",
    "processor_node",
    "formatter_node",
    "create_two_node_graph"
]
