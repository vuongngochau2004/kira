# Agentic RAG Architecture - Complete Documentation

## Overview

The Agentic RAG system is a LangGraph-based multi-agent architecture that enhances the existing K.I.R.A RAG system with intelligent agents for query refinement, retrieval, reranking, generation, critique, and verification.

## Architecture Diagram

```mermaid
graph TB
    subgraph Input["User Input"]
        Query[User Query]
        UserID[User ID]
    end

    subgraph Agents["Agentic Pipeline"]
        QR[Query Refiner<br/>Query Expansion]
        RET[Retrieval Agent<br/>Hybrid Search]
        RR[Reranking Agent<br/>Cross-Encoder]
        GEN[Generation Agent<br/>LLM Response]
        CR[Critique Agent<br/>Quality Check]
        VER[Verification Agent<br/>Final Check]
    end

    subgraph State["RAGState"]
        State[Shared State<br/>TypedDict]
    end

    subgraph Output["Final Output"]
        Response[Response + Citations]
        Metadata[Agent Metadata]
    end

    Query --> QR
    UserID --> QR
    QR -->|Refined Queries| State
    State --> RET
    RET -->|Documents| State
    State --> RR
    RR -->|Reranked Docs| State
    State --> GEN
    GEN -->|Response| State
    State --> CR
    CR -->|Critique| State
    State --> VER
    VER -->|Verified| State
    State --> Response
    State --> Metadata

    style QR fill:#c8e6c9
    style RET fill:#bbdefb
    style RR fill:#fff9c4
    style GEN fill:#f8bbd0
    style CR fill:#e1bee7
    style VER fill:#b2dfdb
    style State fill:#ffccbc
```

## System Components

### 1. RAGState Schema

The central state object that flows through all agents:

```python
class RAGState(TypedDict):
    # Input
    query: str
    user_id: str
    conversation_id: Optional[UUID]

    # Query refinement
    refined_queries: List[str]
    original_query: str

    # Retrieval
    retrieved_docs: List[DocumentWithScore]
    retrieval_metadata: RetrievalMetadata

    # Reranking
    reranked_docs: List[DocumentWithScore]
    reranking_results: List[RerankingResult]

    # Generation
    generated_response: str
    generation_metadata: Dict[str, Any]

    # Critique
    critique_result: CritiqueResult
    critique_iteration: int

    # Verification
    verification_result: VerificationResult
    verification_iteration: int

    # Output
    final_response: str
    final_citations: List[Citation]
    is_final: bool

    # Execution tracking
    agent_results: List[AgentResult]
    current_agent: str
    total_execution_time_ms: float

    # Error handling
    errors: List[str]
    should_fallback: bool
    fallback_reason: Optional[str]
```

### 2. Agent Implementations

#### QueryRefinerAgent
- **Purpose**: Expand and refine user queries
- **Methods**: LLM-based expansion, synonym augmentation
- **Output**: List of refined queries
- **Timeout**: 10 seconds

#### RetrievalAgent
- **Purpose**: Multi-stage document retrieval
- **Strategies**: Dense, BM25, Hybrid with RRF
- **Output**: Retrieved documents with scores
- **Timeout**: 15 seconds

#### RerankingAgent
- **Purpose**: Cross-encoder reranking for precision
- **Method**: Score documents with cross-encoder
- **Output**: Reranked, filtered documents
- **Timeout**: 8 seconds

#### GenerationAgent
- **Purpose**: LLM-based response generation
- **Features**: Streaming, citations, regeneration
- **Output**: Generated response with metadata
- **Timeout**: 20 seconds

#### CritiqueAgent
- **Purpose**: Quality assessment of responses
- **Checks**: Completeness, citation accuracy, coherence
- **Output**: Quality score, improvement suggestions
- **Timeout**: 10 seconds

#### VerificationAgent
- **Purpose**: Final verification before returning
- **Checks**: Factual consistency, citation accuracy
- **Output**: Verification decision and scores
- **Timeout**: 10 seconds

### 3. LangGraph Implementation

The graph orchestrates agents with conditional routing:

```python
# Entry Point
query_refiner → retrieval → reranking → generation → critique → verification → END

# Conditional Edges
- Query refiner: Skip if disabled
- Reranking: Skip if disabled or no documents
- Critique: Loop to generation if regeneration needed
- Verification: Loop to generation if verification failed
- Fallback: Triggered on timeout or errors
```

### 4. Integration Layer

#### AgenticRAGHandler
Implements the `QueryHandlerBase` interface for integration with existing handlers:

```python
class AgenticRAGHandler(QueryHandlerBase):
    async def handle(query, user_id, classification) -> HandlerResult
    async def handle_stream(query, user_id, classification) -> AsyncIterator
    def can_handle(classification) -> bool
```

#### Feature Flags
Percentage-based rollout support:

```python
# Main Agentic RAG flag
agentic_rag_enabled: 0% → 5% → 25% → 100%

# Individual features
query_refiner: 50%
reranking: 50%
critique: 30%
verification: 30%
```

## Configuration

### YAML Configuration

```yaml
# config/agentic-rag-config.yaml
global:
  enable_fallback: true
  fallback_timeout_ms: 45000
  max_total_time_ms: 60000

query_refiner:
  enabled: true
  expansion_count: 3
  use_llm_expansion: true

retrieval:
  enabled: true
  top_k: 10
  strategies: [hybrid]

reranking:
  enabled: true
  top_k: 5
  score_threshold: 0.5

generation:
  enabled: true
  model: "glm-4.5"
  temperature: 0.7

critique:
  enabled: true
  quality_threshold: 0.7
  max_iterations: 2

verification:
  enabled: true
  verification_threshold: 0.8
  max_iterations: 2
```

### Python Configuration

```python
from src.agentic_rag.schemas import AgenticRAGConfig

config = AgenticRAGConfig(
    enable_fallback=True,
    query_refiner_expansion_count=3,
    retrieval_top_k=10,
    reranking_top_k=5,
    generation_model="glm-4.5",
    critique_quality_threshold=0.7,
    verification_verification_threshold=0.8
)
```

## Usage Examples

### Basic Usage

```python
from src.agentic_rag.graph.agentic_rag_graph import create_agentic_rag_graph
from src.agents.llm import LLMClient
from src.agentic_rag.schemas import AgenticRAGConfig

# Create LLM client and config
llm_client = LLMClient()
config = AgenticRAGConfig()

# Create graph
graph = create_agentic_rag_graph(config=config, llm_client=llm_client)

# Execute query
state = await graph.execute(
    query="Điều khoản chấm dứt hợp đồng được quy định như thế nào?",
    user_id="user-123"
)

# Get results
response = state["final_response"]
citations = state["final_citations"]
```

### Handler Integration

```python
from src.agentic_rag.integration.agentic_rag_handler import create_agentic_rag_handler
from src.interfaces.classification import ClassificationResult, Intent

# Create handler
handler = create_agentic_rag_handler(llm_client, agentic_config)

# Create classification
classification = ClassificationResult(
    intent=Intent.RAG,
    confidence=0.95,
    metadata={}
)

# Handle query
result = await handler.handle(
    query="Query about documents",
    user_id="user-123",
    classification=classification
)
```

### Streaming Response

```python
# Stream response
async for chunk in graph.execute_stream(query, user_id):
    if chunk["type"] == "content":
        print(chunk["data"]["text"], end="")
    elif chunk["type"] == "metadata":
        print(f"\nCitations: {len(chunk['data']['citations'])}")
```

### Feature Flags

```python
from src.agentic_rag.integration.feature_flags import create_agentic_rag_feature_flags

# Create feature flags
feature_flags = create_agentic_rag_feature_flags()

# Check rollout
is_enabled = feature_flags.is_agentic_rag_enabled("user-123")

# Get config for user
config = feature_flags.get_config_for_user("user-123")

# Set rollout percentage
feature_flags.set_rollout_percentage("agentic_rag_enabled", 25)
```

## Rollout Strategy

### Phase 1: Internal Testing (0%)
- Testing with internal users
- Validate all agents
- Fix critical bugs

### Phase 2: Beta Rollout (5-10%)
- Small user base
- Monitor performance
- Collect feedback

### Phase 3: Gradual Rollout (25-50%)
- Increase percentage gradually
- Monitor metrics
- Optimize performance

### Phase 4: Full Rollout (100%)
- All users using Agentic RAG
- Continuous monitoring
- Feature enhancements

## Performance Considerations

### Execution Time Budget

- **Total Budget**: 60 seconds
- **Query Refiner**: 10 seconds
- **Retrieval**: 15 seconds
- **Reranking**: 8 seconds
- **Generation**: 20 seconds
- **Critique**: 10 seconds
- **Verification**: 10 seconds

### Optimization Strategies

1. **Parallel Execution**: Run independent agents in parallel
2. **Caching**: Cache refined queries and retrieval results
3. **Early Exit**: Skip agents if not needed
4. **Fallback**: Graceful degradation on timeout

### Monitoring Metrics

- **Total Execution Time**: Target < 30 seconds
- **Agent Success Rate**: Target > 95%
- **Fallback Rate**: Target < 5%
- **Quality Score**: Target > 0.7

## Error Handling

### Agent-Level Errors

Each agent handles its own errors:

```python
try:
    # Agent execution
    result = await agent.execute(state)
except Exception as e:
    # Log error
    logger.error(f"Agent failed: {e}")

    # Add error to state
    state["errors"].append(str(e))

    # Continue with fallback
    state["should_fallback"] = True
```

### System-Level Fallback

If too many errors occur, fall back to simple RAG:

```python
if len(state["errors"]) > 2 or execution_time > timeout:
    # Fallback to simple RAG
    return await simple_rag_handler.handle(query, user_id, classification)
```

## Testing

### Unit Tests

```bash
# Run agent tests
pytest tests/agentic_rag/test-agents.py -v

# Run integration tests
pytest tests/agentic_rag/test-integration.py -v
```

### Performance Tests

```bash
# Run performance benchmarks
pytest tests/agentic_rag/test-performance.py -v
```

### Manual Testing

```bash
# Run usage examples
python examples/agentic-rag-usage.py
```

## Troubleshooting

### Common Issues

1. **Slow Execution**: Increase timeouts or disable non-critical agents
2. **Poor Quality**: Adjust quality thresholds or critique settings
3. **High Fallback Rate**: Investigate agent failures and timeouts
4. **Memory Issues**: Reduce document count or enable pagination

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Enable detailed logging:

```python
config = AgenticRAGConfig(
    log_agent_execution=True,
    log_intermediate_results=True
)
```

## Future Enhancements

### Planned Features

1. **Multi-Agent Collaboration**: Agents working in parallel
2. **Adaptive Configuration**: Auto-tuning based on performance
3. **Advanced Reranking**: List-aware reranking models
4. **Self-Correction**: Automatic error recovery
5. **Explainability**: Agent decision explanations

### Experimental Features

1. **Tool-Using Agents**: Agents with external tools
2. **Memory Systems**: Long-term memory for agents
3. **Hierarchical Agents**: Supervisor-agent architecture
4. **Multi-Modal Support**: Image and video retrieval

## References

- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **RAG Systems**: https://arxiv.org/abs/2312.10997
- **Cross-Encoders**: https://arxiv.org/abs/1911.03377
- **Query Expansion**: https://arxiv.org/abs/2309.00022

## Support

For questions or issues:
- Check documentation in `/docs/agentic-rag/`
- Review examples in `/examples/agentic-rag-usage.py`
- Run tests in `/tests/agentic_rag/`
- Check logs in `/logs/agentic_rag.log`

---

**Version**: 1.0.0
**Last Updated**: 2025-06-10
**Maintainer**: K.I.R.A Development Team
