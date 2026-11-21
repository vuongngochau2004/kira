# LangGraph Fundamentals - Training Guide

**Date**: 2025-06-10  
**Duration**: Day 1 (4 hours)  
**Target Audience**: K.I.R.A Development Team  
**Prerequisites**: Python 3.10+, AsyncIO basics

---

## Learning Objectives

By the end of this training, you will be able to:
1. ✅ Understand LangGraph core concepts and architecture
2. ✅ Define and manage state in LangGraph applications
3. ✅ Build basic agents with LangGraph
4. ✅ Construct graphs with nodes and edges
5. ✅ Integrate LangGraph with existing K.I.R.A architecture

---

## Table of Contents

1. [LangGraph Overview](#1-langgraph-overview)
2. [State Management](#2-state-management)
3. [Agent Basics](#3-agent-basics)
4. [Graph Construction](#4-graph-construction)
5. [Integration with K.I.R.A](#5-integration-with-kira)
6. [Quiz](#6-quiz)
7. [Resources](#7-resources)

---

## 1. LangGraph Overview

### What is LangGraph?

LangGraph is a library for building stateful, multi-actor applications with LLMs. It extends LangChain with:
- **Cyclic graphs** (not just DAGs)
- **State management** across nodes
- **Persistence** and checkpointing
- **Streaming** support
- **Human-in-the-loop** workflows

### Why LangGraph for K.I.R.A?

```
Traditional RAG Pipeline:
Query → Retrieval → Generation → Response
(Single path, no feedback loops)

Agentic RAG with LangGraph:
Query → Query Refiner → Retrieval → Reranking → Generation → Critique → Verification → Response
(Multi-stage, self-correction loops, conditional routing)
```

**Benefits for K.I.R.A:**
1. **Self-Correction**: Critique agent can trigger regeneration
2. **Flexibility**: Conditional routing based on quality scores
3. **Observability**: Track each agent's execution
4. **Maintainability**: Modular agent design

### Core Concepts

#### Graph
A directed graph where nodes represent processing steps and edges define the flow.

```python
from langgraph.graph import StateGraph, END

# Define graph
graph = StateGraph(RAGState)
```

#### Node
A function that processes state and returns updates.

```python
async def retrieval_agent(state: RAGState) -> Dict[str, Any]:
    # Process state
    docs = await retrieve(state["query"])
    # Return updates
    return {"retrieved_docs": docs}
```

#### Edge
Connections between nodes. Can be conditional.

```python
# Simple edge
graph.add_edge("retrieval", "reranking")

# Conditional edge
graph.add_conditional_edges(
    "generation",
    should_regenerate,
    {
        "regenerate": "generation",
        "critique": "critique",
        "end": END
    }
)
```

#### State
TypedDict that flows through the graph.

```python
from typing import TypedDict, List, Optional

class RAGState(TypedDict):
    query: str
    retrieved_docs: List[Document]
    generated_response: Optional[str]
    # ... more fields
```

---

## 2. State Management

### State Schema Definition

State is the central data structure that flows through all nodes.

```python
from typing import TypedDict, List, Optional, Dict, Any
from uuid import UUID

class RAGState(TypedDict):
    # === Input ===
    query: str                          # User's original query
    user_id: str                         # User identifier
    conversation_id: Optional[UUID]     # Conversation context

    # === Query Refinement ===
    refined_queries: List[str]          # Expanded queries
    original_query: str                  # Preserved original

    # === Retrieval ===
    retrieved_docs: List[DocumentWithScore]  # Documents from retrieval
    retrieval_metadata: Dict[str, Any]    # Retrieval stats

    # === Generation ===
    generated_response: str              # LLM response
    generation_metadata: Dict[str, Any]  # Generation stats

    # === Output ===
    final_response: str                  # Final answer
    final_citations: List[Citation]     # Citations
    is_final: bool                       # Completion flag

    # === Execution Tracking ===
    agent_results: List[AgentResult]     # Agent execution history
    current_agent: str                  # Current node
    total_execution_time_ms: float      # Total time

    # === Error Handling ===
    errors: List[str]                   # Error messages
    should_fallback: bool               # Fallback trigger
    fallback_reason: Optional[str]      # Fallback reason
```

### State Updates in Nodes

Nodes return dictionary updates to state:

```python
async def retrieval_agent(state: RAGState) -> Dict[str, Any]:
    """Retrieval agent that updates state"""
    
    # Access current state
    query = state["query"]
    user_id = state["user_id"]
    
    # Perform retrieval
    docs = await hybrid_search(query, user_id)
    
    # Return state updates
    return {
        "retrieved_docs": docs,
        "retrieval_metadata": {
            "count": len(docs),
            "strategy": "hybrid",
            "time_ms": 150
        }
    }
```

### State Reduction Strategy

When multiple nodes update the same field, LangGraph uses a reducer:

```python
from typing import Annotated
from operator import add

# Example: List accumulation
class RAGState(TypedDict):
    # Annotated with reducer
    agent_results: Annotated[List[AgentResult], add]
    errors: Annotated[List[str], add]
```

**Important**: K.I.R.A uses single updates, not accumulations.

---

## 3. Agent Basics

### What is an Agent?

In LangGraph, an agent is a node that:
1. Receives state
2. Performs processing (often with LLM)
3. Returns state updates

### Simple Agent Example

```python
from langchain_core.messages import HumanMessage

async def simple_agent(state: RAGState) -> Dict[str, Any]:
    """Simple LLM-based agent"""
    
    query = state["query"]
    
    # Call LLM
    llm = ChatGLM(model="glm-4.5")
    response = await llm.ainvoke([HumanMessage(content=query)])
    
    # Update state
    return {
        "generated_response": response.content,
        "generation_metadata": {
            "model": "glm-4.5",
            "tokens": response.usage_metadata
        }
    }
```

### Agent with Tools

```python
from langchain_core.tools import tool

@tool
async def search_documents(query: str) -> List[Document]:
    """Search documents in vector store"""
    return await vector_search(query)

async def tool_using_agent(state: RAGState) -> Dict[str, Any]:
    """Agent that uses tools"""
    
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    from langchain_core.prompts import ChatPromptTemplate
    
    # Create agent with tools
    tools = [search_documents]
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant."),
        ("human", "{query}")
    ])
    
    agent = create_openai_functions_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools)
    
    result = await executor.ainvoke({"query": state["query"]})
    
    return {"generated_response": result["output"]}
```

### Agent Patterns

#### 1. Processing Agent
Transforms input to output:
```python
async def query_refiner_agent(state: RAGState) -> Dict[str, Any]:
    query = state["query"]
    refined = await expand_query(query)
    return {"refined_queries": refined}
```

#### 2. Validation Agent
Checks quality and triggers retry:
```python
async def critique_agent(state: RAGState) -> Dict[str, Any]:
    response = state["generated_response"]
    quality_score = await assess_quality(response)
    
    return {
        "critique_result": CritiqueResult(
            score=quality_score,
            should_regenerate=quality_score < 0.7
        )
    }
```

#### 3. Aggregation Agent
Combines multiple results:
```python
async def reranking_agent(state: RAGState) -> Dict[str, Any]:
    docs = state["retrieved_docs"]
    query = state["query"]
    
    reranked = await cross_encoder_rerank(query, docs)
    
    return {"reranked_docs": reranked}
```

---

## 4. Graph Construction

### Basic Graph Structure

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# 1. Define state
class RAGState(TypedDict):
    query: str
    response: str

# 2. Define nodes
async def node_a(state: RAGState):
    print("Node A executing")
    return {"response": "Processed by A"}

async def node_b(state: RAGState):
    print("Node B executing")
    return {"response": state["response"] + " → B"}

# 3. Define conditional routing
def route_decision(state: RAGState):
    score = state.get("quality_score", 0)
    if score > 0.8:
        return "end"
    else:
        return "retry"

# 4. Build graph
graph = StateGraph(RAGState)

# Add nodes
graph.add_node("node_a", node_a)
graph.add_node("node_b", node_b)
graph.add_node("retry", lambda s: {"retry_count": s.get("retry_count", 0) + 1})

# Set entry point
graph.set_entry_point("node_a")

# Add edges
graph.add_edge("node_a", "node_b")
graph.add_conditional_edges(
    "node_b",
    route_decision,
    {
        "end": END,
        "retry": "node_a"  # Loop back
    }
)

# 5. Compile
memory = MemorySaver()
app = graph.compile(checkpointer=memory, interrupt_before=["retry"])

# 6. Execute
config = {"configurable": {"thread_id": "conversation-123"}}
result = app.invoke({"query": "test"}, config)
```

### K.I.R.A Agentic RAG Graph Structure

```python
# 6-Agent Architecture (Current)
from langgraph.graph import StateGraph, END

# Import agents
from src.agentic_rag.agents.query_refiner_agent import query_refiner_agent
from src.agentic_rag.agents.retrieval_agent import retrieval_agent
from src.agentic_rag.agents.reranking_agent import reranking_agent
from src.agentic_rag.agents.generation_agent import generation_agent
from src.agentic_rag.agents.critique_agent import critique_agent
from src.agentic_rag.agents.verification_agent import verification_agent

# Build graph
graph = StateGraph(RAGState)

# Add nodes
graph.add_node("query_refiner", query_refiner_agent)
graph.add_node("retrieval", retrieval_agent)
graph.add_node("reranking", reranking_agent)
graph.add_node("generation", generation_agent)
graph.add_node("critique", critique_agent)
graph.add_node("verification", verification_agent)

# Set entry point
graph.set_entry_point("query_refiner")

# Add edges (linear flow with loops)
graph.add_edge("query_refiner", "retrieval")
graph.add_edge("retrieval", "reranking")
graph.add_edge("reranking", "generation")

# Conditional edge: critique can trigger regeneration
graph.add_conditional_edges(
    "generation",
    should_critique,
    {
        "critique": "critique",
        "end": END
    }
)

# Conditional edge: critique can loop back to generation
graph.add_conditional_edges(
    "critique",
    should_regenerate,
    {
        "regenerate": "generation",
        "verify": "verification"
    }
)

# Conditional edge: verification can loop back
graph.add_conditional_edges(
    "verification",
    should_retry_verification,
    {
        "retry": "generation",
        "end": END
    }
)

# Compile
app = graph.compile(checkpointer=memory)
```

### Graph Visualization

```python
# Visualize graph structure
from IPython.display import Image, display

try:
    display(Image(app.get_graph().draw_mermaid_png()))
except Exception:
    pass  # Visualization not available in all environments
```

### Execution Flow Example

```
Input: {"query": "Hỏi về điều khoản hợp đồng", "user_id": "123"}

[query_refiner] → refined_queries: ["hợp đồng", "điều khoản", ...]
[retrieval] → retrieved_docs: [doc1, doc2, ...]
[reranking] → reranked_docs: [doc1, doc3] (top 5)
[generation] → generated_response: "Theo điều khoản 5..."
[critique] → quality_score: 0.85
[verification] → verification_passed: True

Output: {"final_response": "...", "final_citations": [...]}
```

---

## 5. Integration with K.I.R.A

### Handler Integration Pattern

K.I.R.A uses `QueryHandlerBase` interface for all handlers:

```python
# src/interfaces/handlers.py (ABC-based)
from abc import ABC, abstractmethod

class QueryHandlerBase(ABC):
    @abstractmethod
    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict | None = None
    ) -> HandlerResult:
        pass

    @abstractmethod
    async def handle_stream(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict | None = None
    ) -> AsyncIterator[dict]:
        pass

    @abstractmethod
    def can_handle(self, classification: ClassificationResult) -> bool:
        pass
```

### AgenticRAGHandler Implementation

```python
# src/agentic_rag/integration/agentic_rag_handler.py
from src.interfaces.handlers import QueryHandlerBase, HandlerResult
from src.agentic_rag.graph.agentic_rag_graph import create_agentic_rag_graph
from src.agentic_rag.schemas import AgenticRAGConfig

class AgenticRAGHandler(QueryHandlerBase):
    """LangGraph-based RAG handler with multiple agents"""
    
    def __init__(self, llm_client, agentic_config: AgenticRAGConfig):
        self.llm_client = llm_client
        self.config = agentic_config
        self.graph = create_agentic_rag_graph(agentic_config, llm_client)
    
    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict | None = None
    ) -> HandlerResult:
        """Handle query with Agentic RAG"""
        
        # Execute graph
        state = await self.graph.execute(
            query=query,
            user_id=str(user_id)
        )
        
        # Return HandlerResult
        return HandlerResult(
            content=state["final_response"],
            citations=state["final_citations"],
            metadata={
                "handler": "AgenticRAGHandler",
                "agent_results": state["agent_results"],
                "execution_time_ms": state["total_execution_time_ms"]
            }
        )
    
    async def handle_stream(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict | None = None
    ) -> AsyncIterator[dict]:
        """Stream Agentic RAG response"""
        
        async for chunk in self.graph.execute_stream(query, str(user_id)):
            yield chunk
    
    def can_handle(self, classification: ClassificationResult) -> bool:
        """Check if this handler should handle the query"""
        return classification.is_rag_intent()
    
    def get_config(self) -> HandlerConfig:
        return HandlerConfig(
            name="AgenticRAGHandler",
            timeout_ms=self.config.max_total_time_ms
        )
```

### Dependency Injection Setup

```python
# src/di/container.py
from src.agentic_rag.integration.agentic_rag_handler import create_agentic_rag_handler
from src.agentic_rag.schemas import AgenticRAGConfig

# Register AgenticRAGHandler
await container.register_singleton(
    QueryHandlerBase,
    create_agentic_rag_handler(llm_client, agentic_config)
)
```

### Feature Flag Integration

```python
# src/agentic_rag/integration/feature_flags.py
class AgenticRAGFeatureFlags:
    """Feature flags for Agentic RAG rollout"""
    
    def is_agentic_rag_enabled(self, user_id: str) -> bool:
        """Check if user should get Agentic RAG"""
        rollout_percentage = self.get_rollout("agentic_rag_enabled")
        user_hash = hash(user_id) % 100
        return user_hash < rollout_percentage
```

---

## 6. Quiz

### Part 1: Multiple Choice (10 questions)

**Q1**: What is the main benefit of using LangGraph over traditional RAG pipelines?

A. Faster execution
B. Support for cyclic graphs and self-correction loops
C. Better documentation
D. Lower cost

**Answer**: B

---

**Q2**: How do you define state in LangGraph?

A. Using a Python class
B. Using TypedDict
C. Using a dictionary
D. Using a JSON schema

**Answer**: B

---

**Q3**: What does a node return in LangGraph?

A. The complete state
B. A dictionary of state updates
C. A string response
D. Nothing (side effects only)

**Answer**: B

---

**Q4**: How do you add conditional routing in LangGraph?

A. Using if-else statements
B. Using `add_conditional_edges`
C. Using `add_edge` with conditions
D. Using `set_entry_point`

**Answer**: B

---

**Q5**: What is the entry point in a LangGraph?

A. The first node that executes
B. The last node that executes
C. The checkpoint saver
D. The memory store

**Answer**: A

---

**Q6**: Which K.I.R.A handler interface does AgenticRAGHandler implement?

A. `BaseRouter`
B. `QueryHandlerBase`
C. `ClassificationStrategyBase`
D. `RetrieverBase`

**Answer**: B

---

**Q7**: How do you compile a LangGraph with checkpointing?

A. `graph.compile(memory=MemorySaver())`
B. `graph.compile(checkpointer=MemorySaver())`
C. `graph.build(checkpointer=MemorySaver())`
D. `graph.create(checkpointer=MemorySaver())`

**Answer**: B

---

**Q8**: What happens when a conditional edge returns END?

A. The graph restarts
B. The graph continues to the next node
C. The graph terminates
D. The graph pauses

**Answer**: C

---

**Q9**: How does K.I.R.A integrate AgenticRAGHandler with the existing system?

A. Through direct instantiation
B. Through DI container and QueryHandlerBase interface
C. Through router registry
D. Through configuration files

**Answer**: B

---

**Q10**: What is the purpose of checkpointing in LangGraph?

A. Improve performance
B. Enable state persistence and resume
C. Reduce memory usage
D. Enable streaming

**Answer**: B

---

### Part 2: Practical Exercise

**Exercise**: Build a simple 3-node graph

Create a graph that:
1. Receives a query
2. Transforms it (add prefix "PROCESSED:")
3. Validates it (check if length > 10)
4. If valid → END, if not → loop back to step 2

**Solution**:

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END

class SimpleState(TypedDict):
    query: str
    is_valid: bool
    retry_count: int

def transformer(state: SimpleState):
    query = state["query"]
    return {
        "query": f"PROCESSED:{query}",
        "retry_count": state.get("retry_count", 0) + 1
    }

def validator(state: SimpleState):
    query = state["query"]
    is_valid = len(query) > 10
    return {"is_valid": is_valid}

def route_validator(state: SimpleState):
    if state["is_valid"]:
        return END
    elif state.get("retry_count", 0) < 3:
        return "retry"
    else:
        return END

# Build graph
graph = StateGraph(SimpleState)
graph.add_node("transformer", transformer)
graph.add_node("validator", validator)

graph.set_entry_point("transformer")
graph.add_edge("transformer", "validator")
graph.add_conditional_edges("validator", route_validator, {"retry": "transformer", "end": END})

app = graph.compile()

# Test
result = app.invoke({"query": "short"})
print(result)  # Should have retry_count > 1
```

---

## 7. Resources

### Official Documentation

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Tutorials](https://python.langchain.com/docs/lang_graph)
- [LangGraph Examples](https://github.com/langchain-ai/langgraph/tree/main/examples)

### K.I.R.A Specific

- K.I.R.A Architecture: `/docs/agentic-rag-architecture.md`
- AgenticRAGHandler: `/src/agentic_rag/integration/agentic_rag_handler.py`
- Graph Implementation: `/src/agentic_rag/graph/agentic_rag_graph.py`
- Configuration: `/config/agentic-rag-config.yaml`

### Next Steps

1. **Complete Workshop** (Day 2): Build 2-node graph hands-on
2. **Advanced Patterns** (Day 3): Conditional edges, error handling
3. **Production Readiness** (Day 4): Monitoring, deployment

---

## Key Takeaways

1. ✅ **State is central**: All data flows through TypedDict state
2. ✅ **Nodes return updates**: Not complete state, just updates
3. ✅ **Conditional edges enable loops**: Self-correction is possible
4. ✅ **Checkpointing enables persistence**: Resume from interruptions
5. ✅ **K.I.R.A integration**: Use QueryHandlerBase interface

---

**Training Duration**: 4 hours  
**Quiz Time**: 30 minutes  
**Passing Score**: 80% (8/10 questions)

---

**Last Updated**: 2025-06-10  
**Maintainer**: Backend Lead  
**Next**: Workshop Instructions (Day 2)
