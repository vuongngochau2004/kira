# LangGraph Workshop - Hands-on Instructions

**Date**: 2025-06-10  
**Duration**: Day 2 (4 hours)  
**Prerequisites**: Completed LangGraph Fundamentals (Day 1)  
**Goal**: Build working 2-node and 3-node graphs

---

## Workshop Overview

This workshop provides hands-on experience building LangGraph applications. You will:
1. ✅ Setup development environment
2. ✅ Build a 2-node graph (simple pipeline)
3. ✅ Build a 3-node graph with conditional routing
4. ✅ Test and debug your graphs
5. ✅ Integrate with K.I.R.A components

---

## Part 1: Environment Setup (30 minutes)

### Step 1: Install Dependencies

```bash
# Ensure Python 3.10+
python --version

# Install LangGraph and dependencies
pip install langgraph>=0.0.20
pip install langchain>=0.1.0
pip install langchain-core>=0.1.0

# Install K.I.R.A dependencies
cd /path/to/kira-simple
pip install -r requirements.txt
```

### Step 2: Verify Installation

```bash
# Test LangGraph installation
python -c "from langgraph.graph import StateGraph; print('✅ LangGraph installed')"

# Test K.I.R.A imports
python -c "from src.agentic_rag.graph.agentic_rag_graph import create_agentic_rag_graph; print('✅ K.I.R.A imports working')"
```

### Step 3: Create Workshop Directory

```bash
# Create workshop directory
mkdir -p workshop
cd workshop

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

---

## Part 2: Build 2-Node Graph (60 minutes)

### Objective

Build a simple graph with:
- **Node 1**: Process query (add prefix)
- **Node 2**: Format output (add timestamp)
- **Edge**: Linear flow from Node 1 → Node 2 → END

### Step 1: Define State Schema

Create file `workshop/two_node_graph.py`:

```python
from typing import TypedDict
from datetime import datetime

class TwoNodeState(TypedDict):
    """State for 2-node graph"""
    query: str              # Input query
    processed: str          # Processed output
    timestamp: str          # Timestamp string
```

### Step 2: Implement Nodes

```python
def processor_node(state: TwoNodeState) -> dict:
    """Process query: add PROCESSED prefix"""
    query = state["query"]
    processed = f"PROCESSED:{query}"
    
    print(f"[Processor] Input: {query}")
    print(f"[Processor] Output: {processed}")
    
    return {"processed": processed}


def formatter_node(state: TwoNodeState) -> dict:
    """Format output: add timestamp"""
    processed = state["processed"]
    timestamp = datetime.now().isoformat()
    
    output = f"{processed} | {timestamp}"
    
    print(f"[Formatter] Input: {processed}")
    print(f"[Formatter] Output: {output}")
    
    return {"timestamp": output}
```

### Step 3: Build Graph

```python
from langgraph.graph import StateGraph, END

def create_two_node_graph():
    """Create 2-node graph"""
    
    # Initialize graph
    graph = StateGraph(TwoNodeState)
    
    # Add nodes
    graph.add_node("processor", processor_node)
    graph.add_node("formatter", formatter_node)
    
    # Set entry point
    graph.set_entry_point("processor")
    
    # Add edges
    graph.add_edge("processor", "formatter")
    graph.add_edge("formatter", END)
    
    # Compile
    return graph.compile()
```

### Step 4: Execute Graph

```python
def main():
    """Run 2-node graph"""
    
    # Create graph
    app = create_two_node_graph()
    
    # Execute
    print("\n" + "="*60)
    print("2-Node Graph Execution")
    print("="*60)
    
    result = app.invoke({
        "query": "Hello LangGraph!"
    })
    
    print("\n" + "="*60)
    print("Final Result:")
    print(result)
    print("="*60)


if __name__ == "__main__":
    main()
```

### Step 5: Test

```bash
# Run the graph
python workshop/two_node_graph.py

# Expected output:
# [Processor] Input: Hello LangGraph!
# [Processor] Output: PROCESSED:Hello LangGraph!
# [Formatter] Input: PROCESSED:Hello LangGraph!
# [Formatter] Output: PROCESSED:Hello LangGraph! | 2025-06-10T...
```

### ✅ Checklist

- [ ] Environment setup complete
- [ ] Two-node graph runs without errors
- [ ] Output shows both nodes executed
- [ ] State flows correctly from processor → formatter
- [ ] Final result contains timestamp

---

## Part 3: Build 3-Node Graph with Conditional Routing (90 minutes)

### Objective

Build a graph with:
- **Node 1**: Analyzer (check query length)
- **Node 2**: Short processor (for queries ≤ 10 chars)
- **Node 3**: Long processor (for queries > 10 chars)
- **Conditional Edge**: Route to Node 2 or Node 3 based on length

### Step 1: Define State Schema

Create file `workshop/three_node_graph.py`:

```python
from typing import TypedDict
from enum import Enum

class QueryType(Enum):
    """Query type classification"""
    SHORT = "short"
    LONG = "long"

class ThreeNodeState(TypedDict):
    """State for 3-node graph"""
    query: str              # Input query
    query_type: QueryType   # Query classification
    result: str             # Final result
    processing_time_ms: float  # Processing time
```

### Step 2: Implement Nodes

```python
import time

def analyzer_node(state: ThreeNodeState) -> dict:
    """Analyze query and classify as SHORT or LONG"""
    query = state["query"]
    query_type = QueryType.SHORT if len(query) <= 10 else QueryType.LONG
    
    print(f"[Analyzer] Query: '{query}'")
    print(f"[Analyzer] Length: {len(query)}")
    print(f"[Analyzer] Type: {query_type.value}")
    
    return {"query_type": query_type}


def short_processor_node(state: ThreeNodeState) -> dict:
    """Process short queries (uppercase)"""
    query = state["query"]
    start_time = time.time()
    
    result = query.upper()
    processing_time = (time.time() - start_time) * 1000
    
    print(f"[Short Processor] Input: '{query}'")
    print(f"[Short Processor] Output: '{result}'")
    
    return {
        "result": result,
        "processing_time_ms": processing_time
    }


def long_processor_node(state: ThreeNodeState) -> dict:
    """Process long queries (add prefix)"""
    query = state["query"]
    start_time = time.time()
    
    result = f"[LONG QUERY]: {query}"
    processing_time = (time.time() - start_time) * 1000
    
    print(f"[Long Processor] Input: '{query}'")
    print(f"[Long Processor] Output: '{result}'")
    
    return {
        "result": result,
        "processing_time_ms": processing_time
    }
```

### Step 3: Define Routing Function

```python
def route_by_length(state: ThreeNodeState) -> str:
    """Route to appropriate processor based on query length"""
    query_type = state["query_type"]
    
    print(f"[Router] Routing to: {query_type.value}_processor")
    
    if query_type == QueryType.SHORT:
        return "short_processor"
    else:
        return "long_processor"
```

### Step 4: Build Graph

```python
from langgraph.graph import StateGraph, END

def create_three_node_graph():
    """Create 3-node graph with conditional routing"""
    
    # Initialize graph
    graph = StateGraph(ThreeNodeState)
    
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
    
    # Compile
    return graph.compile()
```

### Step 5: Execute and Test

```python
def main():
    """Run 3-node graph with test cases"""
    
    # Create graph
    app = create_three_node_graph()
    
    # Test cases
    test_queries = [
        "Hi",           # SHORT (2 chars)
        "Hello",        # SHORT (5 chars)
        "Hello World",  # LONG (11 chars)
        "This is a very long query"  # LONG (26 chars)
    ]
    
    print("\n" + "="*60)
    print("3-Node Graph Execution")
    print("="*60)
    
    for query in test_queries:
        print("\n" + "-"*60)
        print(f"Testing query: '{query}'")
        print("-"*60)
        
        result = app.invoke({
            "query": query,
            "processing_time_ms": 0.0
        })
        
        print("\nResult:")
        print(f"  Query: {result['query']}")
        print(f"  Type: {result['query_type'].value}")
        print(f"  Result: {result['result']}")
        print(f"  Processing Time: {result['processing_time_ms']:.2f}ms")


if __name__ == "__main__":
    main()
```

### Step 6: Run Tests

```bash
# Run the graph
python workshop/three_node_graph.py

# Expected output:
# - Short queries routed to short_processor (uppercase)
# - Long queries routed to long_processor (with prefix)
```

### ✅ Checklist

- [ ] 3-node graph runs without errors
- [ ] Short queries (≤10 chars) routed to short_processor
- [ ] Long queries (>10 chars) routed to long_processor
- [ ] Correct processing applied for each type
- [ ] Processing time recorded correctly

---

## Part 4: Debug and Extend (60 minutes)

### Exercise 1: Add Error Handling

Modify the graph to handle empty queries:

```python
def analyzer_node(state: ThreeNodeState) -> dict:
    """Analyze query and classify"""
    query = state["query"]
    
    # Handle empty query
    if not query or not query.strip():
        print("[Analyzer] ⚠️ Empty query detected!")
        return {
            "query_type": QueryType.SHORT,
            "result": "[ERROR]: Empty query",
            "processing_time_ms": 0.0
        }
    
    query_type = QueryType.SHORT if len(query) <= 10 else QueryType.LONG
    return {"query_type": query_type}
```

### Exercise 2: Add Retry Loop

Create a graph that retries up to 3 times:

```python
class RetryState(TypedDict):
    query: str
    retry_count: int
    max_retries: int
    success: bool

def processor_node(state: RetryState) -> dict:
    """Processor that may fail"""
    import random
    
    # Simulate 50% failure rate
    if random.random() < 0.5:
        print(f"[Processor] ❌ Failed (attempt {state['retry_count']})")
        return {"success": False}
    
    print(f"[Processor] ✅ Success (attempt {state['retry_count']})")
    return {"success": True}

def should_retry(state: RetryState) -> str:
    """Decide whether to retry or end"""
    if state["success"]:
        return END
    
    if state["retry_count"] < state["max_retries"]:
        return "retry"
    
    print("[Retry Logic] Max retries reached, giving up")
    return END

def retry_counter(state: RetryState) -> dict:
    """Increment retry counter"""
    return {"retry_count": state["retry_count"] + 1}

# Build retry graph
graph = StateGraph(RetryState)
graph.add_node("processor", processor_node)
graph.add_node("retry_counter", retry_counter)

graph.set_entry_point("processor")
graph.add_conditional_edges("processor", should_retry, {
    "retry": "retry_counter",
    "end": END
})
graph.add_edge("retry_counter", "processor")

app = graph.compile()

# Test
result = app.invoke({
    "query": "test",
    "retry_count": 1,
    "max_retries": 3,
    "success": False
})

print(f"Final: {result['success']}, Attempts: {result['retry_count']}")
```

### Exercise 3: Integrate with K.I.R.A Retrieval

Create a simple RAG-style graph using K.I.R.A components:

```python
from src.retrieval.hybrid import hybrid_search
from src.agents.llm import LLMClient

class SimpleRAGState(TypedDict):
    query: str
    user_id: str
    docs: list
    response: str

async def retrieval_node(state: SimpleRAGState) -> dict:
    """Retrieve documents using K.I.R.A hybrid search"""
    query = state["query"]
    user_id = state["user_id"]
    
    print(f"[Retrieval] Searching for: {query}")
    
    # Use K.I.R.A retrieval
    docs = await hybrid_search(
        query=query,
        user_id=user_id,
        top_k=5
    )
    
    print(f"[Retrieval] Found {len(docs)} documents")
    
    return {"docs": docs}

async def generation_node(state: SimpleRAGState) -> dict:
    """Generate response using LLM"""
    query = state["query"]
    docs = state["docs"]
    
    print(f"[Generation] Generating response for: {query}")
    
    # Build context from docs
    context = "\n".join([doc["text"] for doc in docs])
    
    # Call LLM
    llm = LLMClient()
    prompt = f"Context:\n{context}\n\nQuestion: {query}"
    response = await llm.generate(prompt)
    
    print(f"[Generation] Response generated")
    
    return {"response": response}

# Build RAG graph
from langgraph.graph import StateGraph, END

graph = StateGraph(SimpleRAGState)
graph.add_node("retrieval", retrieval_node)
graph.add_node("generation", generation_node)

graph.set_entry_point("retrieval")
graph.add_edge("retrieval", "generation")
graph.add_edge("generation", END)

app = graph.compile()

# Execute
import asyncio

result = asyncio.run(app.ainvoke({
    "query": "Điều khoản hợp đồng",
    "user_id": "user-123",
    "docs": [],
    "response": ""
}))

print(f"Response: {result['response'][:100]}...")
```

---

## Part 5: Code Review and Q&A (30 minutes)

### Review Checklist

Review your implementations against these criteria:

#### Code Quality
- [ ] State schemas use TypedDict
- [ ] Node functions have clear names and docstrings
- [ ] Routing functions are simple and readable
- [ ] Error handling is present
- [ ] Print statements for debugging

#### Graph Design
- [ ] Entry point clearly set
- [ ] Edges properly connect nodes
- [ ] Conditional edges return valid node names or END
- [ ] No orphaned nodes
- [ ] Graph compiles without errors

#### Testing
- [ ] Multiple test cases executed
- [ ] Edge cases tested (empty, short, long inputs)
- [ ] Output verified
- [ ] Error scenarios tested

### Common Issues and Solutions

**Issue 1**: `KeyError: 'field_name'`
- **Cause**: Field not in state schema
- **Fix**: Add field to TypedDict or ensure node returns it

**Issue 2**: `ValueError: Node 'xxx' not found`
- **Cause**: Typo in node name or node not added
- **Fix**: Check spelling, ensure `graph.add_node()` called

**Issue 3**: Graph returns empty state
- **Cause**: Nodes not returning updates
- **Fix**: Ensure nodes return dict with updates

**Issue 4**: Conditional edge not routing correctly
- **Cause**: Routing function returning wrong value
- **Fix**: Ensure routing function returns exact node name string

**Issue 5**: Infinite loop
- **Cause**: Conditional edge always returning to previous node
- **Fix**: Add loop counter or termination condition

### Q&A Preparation

Prepare questions for the Q&A session:
1. What was the most challenging part?
2. How does LangGraph compare to other workflow tools?
3. How would you design a 4-agent RAG graph?
4. What optimizations would you suggest?

---

## Workshop Completion Criteria

### Must Complete
- ✅ Environment setup successful
- ✅ 2-node graph working
- ✅ 3-node graph with conditional routing working
- ✅ At least 2 extension exercises completed

### Should Complete
- ✅ All 3 extension exercises attempted
- ✅ Code review checklist completed
- ✅ Questions prepared for Q&A

### Nice to Complete
- ✅ K.I.R.A integration exercise completed
- ✅ Custom graph design (beyond exercises)
- ✅ Performance testing conducted

---

## Next Steps

After completing this workshop:
1. **Day 3**: Advanced Patterns Training
2. **Practice**: Build your own 4-agent RAG graph
3. **Review**: Study existing K.I.R.A agentic_rag code
4. **Prepare**: Review production deployment guide

---

## Resources

### Workshop Files
- `workshop/two_node_graph.py`
- `workshop/three_node_graph.py`
- `workshop/retry_graph.py`
- `workshop/simple_rag_graph.py`

### References
- [LangGraph Graph Construction](https://langchain-ai.github.io/langgraph/concepts/low_level/#graph)
- [Conditional Edges](https://langchain-ai.github.io/langgraph/how-tos/logging/)
- [Error Handling](https://python.langchain.com/docs/lang_graph/how_to/errors)

### K.I.R.A Code
- `/src/agentic_rag/graph/agentic_rag_graph.py`
- `/examples/agentic-rag-usage.py`
- `/config/agentic-rag-config.yaml`

---

## Troubleshooting

### Import Errors
```bash
# If getting import errors
export PYTHONPATH="${PYTHONPATH}:/path/to/kira-simple"

# Or use pip install -e . for development mode
cd /path/to/kira-simple
pip install -e .
```

### Async Issues
```python
# If async functions not working, ensure:
# 1. Using await when calling async nodes
# 2. Using app.ainvoke() instead of app.invoke()
# 3. Event loop running properly

# Correct:
result = await app.ainvoke(state)

# Wrong (for async nodes):
result = app.invoke(state)  # Won't work!
```

---

**Workshop Duration**: 4 hours  
**Completion Goal**: Working 3-node graph with conditional routing

---

**Last Updated**: 2025-06-10  
**Instructor**: Backend Lead  
**Next**: Advanced Patterns Training (Day 3)
