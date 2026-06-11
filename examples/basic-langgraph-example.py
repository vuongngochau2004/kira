"""
Basic LangGraph Example - Simple Hello World Graph

This is the simplest possible LangGraph example to demonstrate:
- State definition with TypedDict
- Node creation
- Graph building
- Execution

Use this as a starting point to understand LangGraph basics.
"""

from typing import TypedDict
from langgraph.graph import StateGraph, END


# ============================================================================
# State Definition
# ============================================================================

class BasicState(TypedDict):
    """Minimal state for basic graph"""
    name: str          # Input: name to greet
    greeting: str      # Output: generated greeting


# ============================================================================
# Node Functions
# ============================================================================

def greet_node(state: BasicState) -> dict:
    """Simple greeting node"""

    name = state["name"]
    greeting = f"Hello, {name}!"

    print(f"[Greet Node] Creating greeting for: {name}")

    return {"greeting": greeting}


# ============================================================================
# Graph Construction
# ============================================================================

def create_basic_graph() -> StateGraph:
    """Create basic single-node graph"""

    # Initialize graph
    graph = StateGraph(BasicState)

    # Add node
    graph.add_node("greet", greet_node)

    # Set entry point
    graph.set_entry_point("greet")

    # Add edge to END
    graph.add_edge("greet", END)

    # Compile graph
    return graph.compile()


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Execute basic graph"""

    print("\n" + "="*60)
    print("Basic LangGraph Example")
    print("="*60)

    # Create graph
    app = create_basic_graph()

    # Execute
    test_names = ["Alice", "Bob", "Charlie"]

    for name in test_names:
        print(f"\n{'─'*60}")
        print(f"Input: {name}")
        print('─'*60)

        result = app.invoke({"name": name})

        print(f"\nOutput:")
        print(f"  Name: {result['name']}")
        print(f"  Greeting: {result['greeting']}")

    print("\n" + "="*60)
    print("Example Complete!")
    print("="*60 + "\n")


# ============================================================================
# Module Information
# ============================================================================

if __name__ == "__main__":
    main()

__doc__ = """
Basic LangGraph Example

A minimal example demonstrating:
- TypedDict state definition
- Single node implementation
- Linear graph flow (node → END)
- Basic graph execution

Run: python examples/basic-langgraph-example.py
"""

__all__ = [
    "BasicState",
    "greet_node",
    "create_basic_graph"
]
