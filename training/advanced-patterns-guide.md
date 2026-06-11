# LangGraph Advanced Patterns - Training Guide

**Date**: 2025-06-10  
**Duration**: Day 3 (4 hours)  
**Target Audience**: K.I.R.A Development Team  
**Prerequisites**: Completed Days 1-2 (Fundamentals + Workshop)

---

## Learning Objectives

By the end of this training, you will be able to:
1. ✅ Implement conditional edges with complex routing logic
2. ✅ Handle errors gracefully with fallback mechanisms
3. ✅ Design retry policies with exponential backoff
4. ✅ Implement streaming responses for real-time feedback
5. ✅ Optimize graph performance with parallel execution
6. ✅ Use checkpointing for state persistence

---

## Table of Contents

1. [Conditional Edges](#1-conditional-edges)
2. [Error Handling](#2-error-handling)
3. [Retry Policies](#3-retry-policies)
4. [Streaming Support](#4-streaming-support)
5. [Performance Optimization](#5-performance-optimization)
6. [Checkpointing](#6-checkpointing)
7. [Exercises](#7-exercises)
8. [Quiz](#8-quiz)

---

## 1. Conditional Edges

### Overview

Conditional edges enable dynamic routing based on state. Unlike simple edges, conditional edges:
- Can route to multiple destinations
- Make decisions based on state values
- Enable loops and self-correction
- Support complex routing logic

### Basic Conditional Edge

```python
from typing import Literal
from langgraph.graph import StateGraph, END

def route_decision(state: RAGState) -> Literal["generation", "verification", END]:
    """Route based on generation quality"""
    
    quality_score = state.get("quality_score", 0.0)
    iteration = state.get("generation_iteration", 0)
    
    # High quality → verify
    if quality_score > 0.8:
        return "verification"
    
    # Low quality but under max iterations → regenerate
    elif quality_score < 0.6 and iteration < 3:
        return "generation"
    
    # Otherwise end with current result
    else:
        return END

# Add to graph
graph.add_conditional_edges(
    "generation",
    route_decision,
    {
        "generation": "generation",  # Loop back
        "verification": "verification",
        "end": END
    }
)
```

### Complex Routing Logic

```python
def intelligent_router(state: RAGState) -> Literal["rerank", "generate", "fallback", END]:
    """Multi-factor routing decision"""
    
    # Extract factors
    retrieved_count = len(state.get("retrieved_docs", []))
    query_complexity = state.get("query_complexity", "medium")
    confidence = state.get("retrieval_confidence", 0.0)
    
    # No documents → fallback
    if retrieved_count == 0:
        return "fallback"
    
    # Too many documents → rerank
    if retrieved_count > 10:
        return "rerank"
    
    # Low confidence with complex query → fallback
    if confidence < 0.5 and query_complexity == "high":
        return "fallback"
    
    # Good to generate
    return "generate"

# Add to graph
graph.add_conditional_edges(
    "retrieval",
    intelligent_router,
    {
        "rerank": "reranking",
        "generate": "generation",
        "fallback": "fallback_handler",
        "end": END
    }
)
```

### State-Based Conditional Edges

```python
from enum import Enum

class QueryIntent(Enum):
    DOCUMENT_SEARCH = "document_search"
    GENERAL_CHAT = "general_chat"
    CLARIFICATION_NEEDED = "clarification_needed"

def intent_based_router(state: RAGState) -> Literal["rag", "chat", "clarify", END]:
    """Route based on query intent"""
    
    intent = state.get("query_intent", QueryIntent.GENERAL_CHAT)
    
    if intent == QueryIntent.DOCUMENT_SEARCH:
        return "rag"
    elif intent == QueryIntent.GENERAL_CHAT:
        return "chat"
    elif intent == QueryIntent.CLARIFICATION_NEEDED:
        return "clarify"
    else:
        return END

graph.add_conditional_edges(
    "query_classifier",
    intent_based_router,
    {
        "rag": "rag_handler",
        "chat": "chat_handler",
        "clarify": "clarification_agent",
        "end": END
    }
)
```

### Multi-Condition Routing

```python
def complex_router(state: RAGState) -> str:
    """Router with multiple conditions"""
    
    # Condition 1: Quality threshold
    quality = state.get("response_quality", 0.0)
    if quality < 0.5:
        return "regenerate"
    
    # Condition 2: Citation check
    citation_count = len(state.get("citations", []))
    if citation_count == 0:
        return "retrieve_more"
    
    # Condition 3: Iteration limit
    iterations = state.get("generation_iterations", 0)
    if iterations >= 3:
        return "accept"
    
    # Condition 4: User preference
    user_preference = state.get("user_preference", "balanced")
    if user_preference == "fast":
        return "accept"
    
    # Default: verify
    return "verify"

graph.add_conditional_edges(
    "generation",
    complex_router,
    {
        "regenerate": "generation",
        "retrieve_more": "retrieval",
        "accept": END,
        "verify": "verification"
    }
)
```

---

## 2. Error Handling

### Node-Level Error Handling

```python
import logging

logger = logging.getLogger(__name__)

async def safe_retrieval_agent(state: RAGState) -> Dict[str, Any]:
    """Retrieval agent with error handling"""
    
    try:
        query = state["query"]
        user_id = state["user_id"]
        
        # Perform retrieval
        docs = await hybrid_search(query, user_id)
        
        return {
            "retrieved_docs": docs,
            "retrieval_status": "success"
        }
    
    except TimeoutError as e:
        logger.error(f"Retrieval timeout: {e}")
        return {
            "retrieved_docs": [],
            "retrieval_status": "timeout",
            "errors": state.get("errors", []) + [f"Retrieval timeout: {e}"]
        }
    
    except Exception as e:
        logger.error(f"Retrieval failed: {e}", exc_info=True)
        return {
            "retrieved_docs": [],
            "retrieval_status": "error",
            "errors": state.get("errors", []) + [f"Retrieval error: {e}"]
        }
```

### Graph-Level Error Handling

```python
def handle_errors(state: RAGState) -> str:
    """Check errors and decide next action"""
    
    errors = state.get("errors", [])
    error_count = len(errors)
    
    # No errors → continue
    if error_count == 0:
        return "continue"
    
    # Too many errors → fallback
    if error_count >= 3:
        return "fallback"
    
    # Check error types
    critical_errors = [e for e in errors if "critical" in e.lower()]
    if critical_errors:
        return "fallback"
    
    # Recoverable errors → retry
    return "retry"

graph.add_conditional_edges(
    "error_check",
    handle_errors,
    {
        "continue": "next_node",
        "retry": "retry_node",
        "fallback": "fallback_handler",
        "end": END
    }
)
```

### Fallback Handler

```python
async def fallback_handler(state: RAGState) -> Dict[str, Any]:
    """Fallback to simple RAG when Agentic RAG fails"""
    
    logger.warning("Falling back to simple RAG")
    
    try:
        # Use simple RAG as fallback
        from src.handlers.rag import RAGHandler
        
        simple_rag = RAGHandler()
        result = await simple_rag.handle(
            query=state["query"],
            user_id=state["user_id"],
            classification=state.get("classification")
        )
        
        return {
            "final_response": result.content,
            "final_citations": result.citations,
            "fallback_used": True,
            "fallback_reason": state.get("errors", ["Unknown"])[-1]
        }
    
    except Exception as e:
        logger.error(f"Fallback also failed: {e}")
        return {
            "final_response": "Sorry, I encountered an error. Please try again.",
            "final_citations": [],
            "fallback_used": True,
            "fallback_reason": f"Fallback error: {e}"
        }
```

### Timeout Handling

```python
import asyncio

async def timeout_wrapper(node_func, state: RAGState, timeout_ms: int):
    """Wrap node execution with timeout"""
    
    try:
        result = await asyncio.wait_for(
            node_func(state),
            timeout=timeout_ms / 1000
        )
        return result, None
    
    except asyncio.TimeoutError:
        error = f"Node execution timeout after {timeout_ms}ms"
        return None, error

async def safe_generation_agent(state: RAGState) -> Dict[str, Any]:
    """Generation agent with timeout"""
    
    TIMEOUT_MS = 20000  # 20 seconds
    
    result, error = await timeout_wrapper(
        generation_logic,
        state,
        TIMEOUT_MS
    )
    
    if error:
        return {
            "generated_response": "",
            "generation_status": "timeout",
            "errors": state.get("errors", []) + [error]
        }
    
    return result

async def generation_logic(state: RAGState) -> Dict[str, Any]:
    """Actual generation logic"""
    # ... generation code
    pass
```

---

## 3. Retry Policies

### Basic Retry with Counter

```python
class RetryState(TypedDict):
    query: str
    retry_count: int
    max_retries: int
    success: bool
    result: str

def retry_router(state: RetryState) -> Literal["retry", "success", "give_up"]:
    """Decide whether to retry or give up"""
    
    if state["success"]:
        return "success"
    
    if state["retry_count"] < state["max_retries"]:
        return "retry"
    
    return "give_up"

def increment_retry(state: RetryState) -> Dict[str, Any]:
    """Increment retry counter"""
    return {
        "retry_count": state["retry_count"] + 1
    }

graph.add_conditional_edges(
    "processor",
    retry_router,
    {
        "retry": "retry_counter",
        "success": END,
        "give_up": "fallback"
    }
)

graph.add_edge("retry_counter", "processor")
```

### Exponential Backoff

```python
import asyncio
import time

class BackoffState(TypedDict):
    query: str
    retry_count: int
    delay_ms: int
    max_retries: int

async def processor_with_backoff(state: BackoffState) -> Dict[str, Any]:
    """Processor with exponential backoff"""
    
    retry_count = state["retry_count"]
    
    # Calculate backoff delay: 100ms * 2^retry_count
    delay = 100 * (2 ** retry_count)
    
    print(f"[Processor] Attempt {retry_count + 1}, delay: {delay}ms")
    
    # Wait before retry
    await asyncio.sleep(delay / 1000)
    
    # Try processing
    try:
        # ... processing logic
        success = True  # Assume success
        return {"success": success, "delay_ms": delay}
    except Exception as e:
        return {"success": False, "delay_ms": delay, "error": str(e)}
```

### Conditional Retry

```python
def should_retry(state: RAGState) -> bool:
    """Decide if retry is worth attempting"""
    
    errors = state.get("errors", [])
    retry_count = state.get("retry_count", 0)
    
    # Don't retry if too many attempts
    if retry_count >= 3:
        return False
    
    # Don't retry on critical errors
    for error in errors:
        if "authentication" in error.lower():
            return False  # Auth errors won't be fixed by retry
        if "permission" in error.lower():
            return False  # Permission errors
    
    # Retry on temporary errors
    for error in errors:
        if "timeout" in error.lower():
            return True
        if "connection" in error.lower():
            return True
        if "rate limit" in error.lower():
            return True
    
    return False

def retry_router(state: RAGState) -> Literal["retry", "fallback", END]:
    """Smart retry router"""
    
    if state.get("success", False):
        return END
    
    if should_retry(state):
        return "retry"
    
    return "fallback"

graph.add_conditional_edges(
    "processor",
    retry_router,
    {
        "retry": "retry_counter",
        "fallback": "fallback_handler",
        "end": END
    }
)
```

---

## 4. Streaming Support

### Basic Streaming

```python
from langgraph.graph import StateGraph

async def streaming_generation_agent(state: RAGState) -> AsyncIterator[Dict[str, Any]]:
    """Generation agent that streams tokens"""
    
    query = state["query"]
    context = state.get("context", "")
    
    # Initialize streaming
    yield {
        "type": "generation_start",
        "data": {"query": query}
    }
    
    # Stream LLM response
    llm = LLMClient()
    async for token in llm.astream_generate(query, context):
        yield {
            "type": "token",
            "data": {"token": token}
        }
    
    # Complete streaming
    yield {
        "type": "generation_complete",
        "data": {}
    }
```

### Graph Streaming Execution

```python
async def execute_stream(graph, query: str, user_id: str):
    """Execute graph with streaming"""
    
    config = {"configurable": {"thread_id": f"stream-{user_id}"}}
    
    async for chunk in graph.astream(
        {"query": query, "user_id": user_id},
        config
    ):
        chunk_type = chunk.get("type")
        chunk_data = chunk.get("data", {})
        
        if chunk_type == "agent_progress":
            print(f"\n[Agent: {chunk_data['agent']}]")
        
        elif chunk_type == "token":
            print(chunk_data["token"], end="", flush=True)
        
        elif chunk_type == "generation_complete":
            print("\n[Complete]")
        
        elif chunk_type == "error":
            print(f"\n[Error: {chunk_data.get('message')}]")
        
        elif chunk_type == "done":
            print(f"\n[Execution time: {chunk_data.get('time_ms')}ms]")
```

### K.I.R.A Streaming Pattern

```python
async def handle_stream(
    self,
    query: str,
    user_id: str,
    classification: ClassificationResult
) -> AsyncIterator[dict]:
    """Stream Agentic RAG response"""
    
    # Yield routing info
    yield {
        "type": "routing",
        "data": {
            "handler": "AgenticRAGHandler",
            "intent": classification.intent.value,
            "confidence": classification.confidence
        }
    }
    
    # Stream graph execution
    async for chunk in self.graph.execute_stream(query, user_id):
        
        # Agent progress
        if chunk["type"] == "agent_progress":
            yield {
                "type": "agent_progress",
                "data": {
                    "agent": chunk["data"]["agent"],
                    "status": chunk["data"]["status"],
                    "time_ms": chunk["data"]["time_ms"]
                }
            }
        
        # Content chunks
        elif chunk["type"] == "content":
            yield {
                "type": "content",
                "data": {
                    "text": chunk["data"]["text"]
                }
            }
        
        # Metadata
        elif chunk["type"] == "metadata":
            yield {
                "type": "metadata",
                "data": {
                    "citations": chunk["data"]["citations"],
                    "quality_score": chunk["data"]["quality_score"]
                }
            }
        
        # Errors
        elif chunk["type"] == "error":
            yield {
                "type": "error",
                "data": {
                    "message": chunk["data"]["message"]
                }
            }
    
    # Yield completion
    yield {
        "type": "done",
        "data": {}
    }
```

---

## 5. Performance Optimization

### Parallel Execution

```python
import asyncio

async def parallel_retrieval(state: RAGState) -> Dict[str, Any]:
    """Run multiple retrieval strategies in parallel"""
    
    query = state["query"]
    user_id = state["user_id"]
    
    # Run dense and BM25 in parallel
    dense_task = asyncio.create_task(dense_search(query, user_id))
    bm25_task = asyncio.create_task(bm25_search(query, user_id))
    
    # Wait for both
    dense_docs, bm25_docs = await asyncio.gather(
        dense_task,
        bm25_task
    )
    
    # Combine results
    all_docs = dense_docs + bm25_docs
    
    return {
        "retrieved_docs": all_docs,
        "retrieval_metadata": {
            "strategies": ["dense", "bm25"],
            "parallel": True
        }
    }
```

### Caching Strategy

```python
from functools import lru_cache
import hashlib

def get_query_hash(query: str) -> str:
    """Generate hash for query caching"""
    return hashlib.md5(query.encode()).hexdigest()

# Simple cache
query_cache = {}

async def cached_retrieval(state: RAGState) -> Dict[str, Any]:
    """Retrieval with caching"""
    
    query = state["query"]
    query_hash = get_query_hash(query)
    
    # Check cache
    if query_hash in query_cache:
        print(f"[Cache Hit] Using cached results for query")
        return query_cache[query_hash]
    
    # Cache miss - perform retrieval
    docs = await hybrid_search(query, state["user_id"])
    
    # Store in cache
    result = {
        "retrieved_docs": docs,
        "cache_hit": False
    }
    query_cache[query_hash] = result
    
    return result
```

### Early Exit Optimization

```python
def should_skip_reranking(state: RAGState) -> bool:
    """Decide if reranking can be skipped"""
    
    retrieved_docs = state.get("retrieved_docs", [])
    
    # Skip if few documents
    if len(retrieved_docs) <= 5:
        return True
    
    # Skip if scores are already high
    avg_score = sum(doc.score for doc in retrieved_docs) / len(retrieved_docs)
    if avg_score > 0.8:
        return True
    
    # Perform reranking
    return False

def conditional_reranking_router(state: RAGState) -> Literal["rerank", "generate"]:
    """Skip reranking if not needed"""
    
    if should_skip_reranking(state):
        return "generate"
    
    return "rerank"

graph.add_conditional_edges(
    "retrieval",
    conditional_reranking_router,
    {
        "rerank": "reranking",
        "generate": "generation"
    }
)
```

---

## 6. Checkpointing

### Memory Checkpointing

```python
from langgraph.checkpoint.memory import MemorySaver

# Create checkpoint saver
memory = MemorySaver()

# Compile graph with checkpointing
app = graph.compile(
    checkpointer=memory,
    interrupt_before=["critique"]  # Pause before critique
)

# Execute with thread ID for checkpointing
config = {"configurable": {"thread_id": "user-123-conversation-1"}}

# First execution
result = app.invoke({"query": "initial query"}, config)

# Resume after interruption
# ... human intervention or external action ...

# Resume execution
result = app.invoke(None, config)  # None state = resume from checkpoint
```

### PostgreSQL Checkpointing

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Create PostgreSQL checkpoint saver
from sqlalchemy import create_engine

db_url = "postgresql://user:pass@localhost:5432/kira_dev"
engine = create_engine(db_url)
checkpointer = PostgresSaver.from_conn_string(db_url)

# Compile with persistent checkpointing
app = graph.compile(checkpointer=checkpointer)

# Execute with persistent checkpoint
config = {"configurable": {"thread_id": "user-123"}}
result = app.invoke({"query": "test"}, config)

# Can resume even after server restart
result = app.invoke(None, config)  # Resume from saved state
```

### Checkpoint for Human-in-the-Loop

```python
async def human_in_loop_graph(state: RAGState) -> Dict[str, Any]:
    """Graph that pauses for human approval"""
    
    # ... generation logic
    
    # Add checkpoint for human review
    state["pending_approval"] = True
    
    return state

# Compile with interrupt
app = graph.compile(
    checkpointer=memory,
    interrupt_before=["verification"]
)

# Execute - will pause before verification
config = {"configurable": {"thread_id": "review-123"}}
state = app.invoke({"query": "test"}, config)

# ... human reviews state ...

# Update state with approval
state_update = {"approved": True}

# Resume execution
final_state = app.invoke(state_update, config)
```

---

## 7. Exercises

### Exercise 1: Conditional Routing with Quality Thresholds

Create a graph that routes based on retrieval quality:

```python
def quality_based_router(state: RAGState) -> str:
    """Route based on retrieval quality"""
    
    avg_score = calculate_average_score(state["retrieved_docs"])
    doc_count = len(state["retrieved_docs"])
    
    # High quality → direct to generation
    if avg_score > 0.8 and doc_count >= 5:
        return "generation"
    
    # Medium quality → rerank
    elif avg_score > 0.5 and doc_count >= 3:
        return "reranking"
    
    # Low quality → retrieve again with different strategy
    else:
        return "retrieval"

# Implement this router in a graph
```

### Exercise 2: Error Recovery with Graceful Degradation

Create a graph that handles multiple error scenarios:

```python
def error_recovery_router(state: RAGState) -> str:
    """Recover from errors gracefully"""
    
    errors = state.get("errors", [])
    last_error = errors[-1] if errors else ""
    
    # Analyze error type
    if "timeout" in last_error:
        # Retry with longer timeout
        return "retry_with_timeout"
    
    elif "api limit" in last_error:
        # Wait and retry
        return "wait_and_retry"
    
    elif "no documents" in last_error:
        # Fallback to general chat
        return "chat_fallback"
    
    else:
        # Generic fallback
        return "generic_fallback"

# Implement with appropriate nodes
```

### Exercise 3: Streaming with Agent Progress

Create a streaming graph that reports progress:

```python
async def streaming_rag_graph(query: str, user_id: str):
    """Stream RAG execution with progress updates"""
    
    async for chunk in execute_agentic_rag_stream(query, user_id):
        if chunk["type"] == "agent_start":
            print(f"\n▶ {chunk['data']['agent']}")
        
        elif chunk["type"] == "agent_progress":
            status = chunk["data"]["status"]
            print(f"  Status: {status}")
        
        elif chunk["type"] == "content":
            print(chunk["data"]["text"], end="", flush=True)
        
        elif chunk["type"] == "agent_complete":
            time_ms = chunk["data"]["time_ms"]
            print(f"  ✓ Completed in {time_ms}ms")
        
        elif chunk["type"] == "done":
            print(f"\n✓ Total time: {chunk['data']['total_time']}ms")

# Implement the streaming execution
```

### Exercise 4: Performance Optimization

Optimize a graph for faster execution:

```python
# 1. Add caching to retrieval node
# 2. Implement parallel execution where possible
# 3. Add early exit conditions
# 4. Use checkpointing to resume long-running graphs

# Measure before/after performance
import time

start = time.time()
result = await app.invoke(state)
duration = time.time() - start

print(f"Execution time: {duration:.2f}s")
```

---

## 8. Quiz

### Part 1: Multiple Choice (10 questions)

**Q1**: How do you define a conditional edge in LangGraph?

A. Using `add_edge()` with if statements
B. Using `add_conditional_edges()` with a routing function
C. Using `set_entry_point()` with conditions
D. Using Python if/else in node functions

**Answer**: B

---

**Q2**: What is the purpose of checkpointing in LangGraph?

A. Improve performance
B. Enable state persistence and resume
C. Add retry logic
D. Enable streaming

**Answer**: B

---

**Q3**: How do you handle errors in a node?

A. Use try/except and return error state
B. Let errors propagate to graph level
C. Use fallback handler only
D. Ignore errors and continue

**Answer**: A

---

**Q4**: What is exponential backoff used for?

A. Improve performance
B. Reduce retry load on failed services
C. Increase memory usage
D. Speed up retries

**Answer**: B

---

**Q5**: How do you implement streaming in LangGraph?

A. Use `astream()` instead of `invoke()`
B. Use `stream()` parameter
C. Use asyncio streams
D. Use callbacks

**Answer**: A

---

**Q6**: What is early exit optimization?

A. Skip nodes when not needed
B. Exit graph on first error
C. Stop streaming early
D. Exit graph immediately

**Answer**: A

---

**Q7**: How do you run operations in parallel in LangGraph?

A. Use `asyncio.gather()` in node
B. Use `parallel_execution` flag
C. Use multiple threads
D. Use separate graphs

**Answer**: A

---

**Q8**: What does `interrupt_before` do?

A. Pause execution before a node for human intervention
B. Stop execution before timeout
C. Interrupt node execution
D. Pause before errors

**Answer**: A

---

**Q9**: How do you implement retry logic?

A. Use conditional edge to loop back
B. Use `retry()` decorator
C. Use while loop in node
D. Use retry middleware

**Answer**: A

---

**Q10**: What is the benefit of caching in graphs?

A. Reduced memory usage
B. Faster execution for repeated queries
C. Better error handling
D. Improved streaming

**Answer**: B

---

## Key Takeaways

1. ✅ **Conditional edges enable dynamic routing**: Make decisions based on state
2. ✅ **Error handling should be at node level**: Use try/except in each node
3. ✅ **Retry with exponential backoff**: Don't overwhelm failing services
4. ✅ **Streaming provides real-time feedback**: Use `astream()` for long-running graphs
5. ✅ **Optimize with caching and parallel execution**: Reduce latency
6. ✅ **Checkpointing enables persistence**: Resume from interruptions

---

## Next Steps

1. **Practice**: Build your own optimized graph
2. **Review**: Study K.I.R.A agentic_rag implementation
3. **Prepare**: Production deployment considerations (Day 4)

---

**Training Duration**: 4 hours  
**Quiz Time**: 30 minutes  
**Passing Score**: 80% (8/10 questions)

---

**Last Updated**: 2025-06-10  
**Maintainer**: Backend Lead  
**Next**: Production Readiness (Day 4)
