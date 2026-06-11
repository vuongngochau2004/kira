# LangGraph Production Readiness - Training Guide

**Date**: 2025-06-10  
**Duration**: Day 4 (4 hours)  
**Target Audience**: K.I.R.A Development Team  
**Prerequisites**: Completed Days 1-3 (Fundamentals + Workshop + Advanced Patterns)

---

## Learning Objectives

By the end of this training, you will be able to:
1. ✅ Implement monitoring and tracing for LangGraph applications
2. ✅ Understand deployment considerations for production
3. ✅ Apply security best practices
4. ✅ Configure performance optimization
5. ✅ Set up observability and alerting
6. ✅ Prepare for production rollout

---

## Table of Contents

1. [Monitoring and Tracing](#1-monitoring-and-tracing)
2. [Deployment Considerations](#2-deployment-considerations)
3. [Security Best Practices](#3-security-best-practices)
4. [Performance Optimization](#4-performance-optimization)
5. [Observability and Alerting](#5-observability-and-alerting)
6. [Production Rollout Strategy](#6-production-rollout-strategy)
7. [Best Practices](#7-best-practices)
8. [Q&A and Planning](#8-qa-and-planning)

---

## 1. Monitoring and Tracing

### LangSmith Integration

LangSmith is the official observability platform for LangChain/LangGraph applications.

```python
import os
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver

# Enable LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "lsv2_your_api_key_here"
os.environ["LANGCHAIN_PROJECT"] = "kira-agentic-rag"

# Configure LangSmith for production
from langchain.callbacks import tracing_v2_enabled

# Tracing will automatically capture:
# - Node execution times
# - LLM calls
# - Tool invocations
# - State transitions
# - Error information
```

### Custom Metrics Tracking

```python
import time
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
graph_executions = Counter(
    'agentic_rag_graph_executions_total',
    'Total graph executions',
    ['status', 'user_id']
)

graph_duration = Histogram(
    'agentic_rag_graph_duration_seconds',
    'Graph execution duration',
    ['agent']
)

agent_quality_score = Gauge(
    'agentic_rag_agent_quality_score',
    'Agent quality scores',
    ['agent_name']
)

async def monitored_node(state: RAGState) -> Dict[str, Any]:
    """Node with monitoring"""
    
    start_time = time.time()
    agent_name = "retrieval"
    
    try:
        # Execute node logic
        result = await retrieval_logic(state)
        
        # Record success
        graph_executions.labels(status='success', user_id=state['user_id']).inc()
        
        # Record duration
        duration = time.time() - start_time
        graph_duration.labels(agent=agent_name).observe(duration)
        
        # Record quality
        if 'quality_score' in result:
            agent_quality_score.labels(agent_name=agent_name).set(result['quality_score'])
        
        return result
    
    except Exception as e:
        # Record error
        graph_executions.labels(status='error', user_id=state['user_id']).inc()
        raise
```

### Structured Logging

```python
import structlog

# Configure structured logging
logger = structlog.get_logger()

async def logged_node(state: RAGState) -> Dict[str, Any]:
    """Node with structured logging"""
    
    node_name = "generation"
    user_id = state["user_id"]
    
    logger.info(
        "node_execution_start",
        node_name=node_name,
        user_id=user_id,
        query_length=len(state["query"])
    )
    
    start_time = time.time()
    
    try:
        result = await generation_logic(state)
        duration = time.time() - start_time
        
        logger.info(
            "node_execution_success",
            node_name=node_name,
            user_id=user_id,
            duration_ms=duration * 1000,
            output_length=len(result.get("generated_response", ""))
        )
        
        return result
    
    except Exception as e:
        duration = time.time() - start_time
        
        logger.error(
            "node_execution_error",
            node_name=node_name,
            user_id=user_id,
            duration_ms=duration * 1000,
            error=str(e),
            error_type=type(e).__name__
        )
        raise
```

### Distributed Tracing

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger import JaegerExporter

# Setup Jaeger tracing
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

tracer = trace.get_tracer(__name__)

async def traced_node(state: RAGState) -> Dict[str, Any]:
    """Node with distributed tracing"""
    
    with tracer.start_as_current_span("retrieval_node") as span:
        # Add attributes
        span.set_attribute("user_id", state["user_id"])
        span.set_attribute("query_length", len(state["query"]))
        
        # Execute logic
        result = await retrieval_logic(state)
        
        # Record results
        span.set_attribute("doc_count", len(result.get("retrieved_docs", [])))
        
        return result
```

---

## 2. Deployment Considerations

### Environment Configuration

```yaml
# config/environments/production.yaml
langgraph:
  # Checkpoint configuration
  checkpointing:
    enabled: true
    backend: postgresql  # or sqlite for dev
    connection_string: ${POSTGRES_URL}
    
  # Execution settings
  execution:
    max_concurrent_graphs: 100
    timeout_per_graph: 60  # seconds
    max_retries_per_node: 3
    
  # Monitoring
  monitoring:
    langsmith_enabled: true
    prometheus_enabled: true
    jaeger_enabled: true
    
  # Security
  security:
    enable_auth: true
    rate_limiting:
      enabled: true
      requests_per_minute: 60
    api_key_required: true
```

### Docker Deployment

```dockerfile
# Dockerfile for LangGraph application
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY config/ ./config/

# Environment variables
ENV PYTHONPATH=/app
ENV LANGCHAIN_TRACING_V2=true
ENV LANGCHAIN_PROJECT=kira-production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kira-agentic-rag
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kira-agentic-rag
  template:
    metadata:
      labels:
        app: kira-agentic-rag
    spec:
      containers:
      - name: app
        image: kira-agentic-rag:latest
        ports:
        - containerPort: 8000
        env:
        - name: POSTGRES_URL
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: url
        - name: LANGCHAIN_API_KEY
          valueFrom:
            secretKeyRef:
              name: langchain-secrets
              key: api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Database Migration

```python
# Alembic migration for checkpointing
"""alembic migration for langgraph checkpointing

Revision ID: 001_add_checkpoint_tables
Create Date: 2025-06-10

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create checkpoint tables
    op.create_table(
        'checkpoints',
        sa.Column('thread_id', sa.String(), nullable=False),
        sa.Column('checkpoint_id', sa.String(), nullable=False),
        sa.Column('checkpoint', sa.JSON(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('thread_id', 'checkpoint_id')
    )
    op.create_index('idx_checkpoints_thread_id', 'checkpoints', ['thread_id'])

def downgrade():
    op.drop_index('idx_checkpoints_thread_id', table_name='checkpoints')
    op.drop_table('checkpoints')
```

---

## 3. Security Best Practices

### API Key Management

```python
import os
from cryptography.fernet import Fernet

# Never hardcode API keys
# Use environment variables or secret management

def get_api_key(service: str) -> str:
    """Get API key from environment with validation"""
    
    api_key = os.getenv(f"{service.upper()}_API_KEY")
    
    if not api_key:
        raise ValueError(f"Missing API key for {service}")
    
    if api_key.startswith("sk-") or api_key.startswith("lsv2_"):
        return api_key
    
    raise ValueError(f"Invalid API key format for {service}")

# For sensitive secrets, use encryption
def encrypt_secret(secret: str, key: bytes) -> bytes:
    """Encrypt secret for storage"""
    f = Fernet(key)
    return f.encrypt(secret.encode())

def decrypt_secret(encrypted: bytes, key: bytes) -> str:
    """Decrypt secret for use"""
    f = Fernet(key)
    return f.decrypt(encrypted).decode()
```

### Input Validation

```python
from typing import Optional
import re

def validate_query(query: str) -> str:
    """Validate and sanitize user query"""
    
    # Check length
    if not query or len(query) > 10000:
        raise ValueError("Query must be 1-10000 characters")
    
    # Check for injection patterns
    dangerous_patterns = [
        r"<script[^>]*>.*?</script>",  # XSS
        r"DROP TABLE",  # SQL injection
        r"\$\{.*\}",  # Template injection
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            raise ValueError("Query contains dangerous patterns")
    
    # Sanitize
    query = query.strip()
    
    return query

def validate_user_id(user_id: str) -> str:
    """Validate user ID format"""
    
    # Check format
    if not re.match(r"^[\w-]+$", user_id):
        raise ValueError("Invalid user ID format")
    
    # Check length
    if len(user_id) > 100:
        raise ValueError("User ID too long")
    
    return user_id
```

### Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi import FastAPI, Request

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/chat")
@limiter.limit("60/minute")  # 60 requests per minute
async def chat_endpoint(request: Request, query: str):
    """Chat endpoint with rate limiting"""
    
    # Validate input
    validated_query = validate_query(query)
    
    # Process query
    result = await process_query(validated_query)
    
    return result
```

### Authentication and Authorization

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(token: str = Depends(security)) -> str:
    """Verify JWT token"""
    
    try:
        payload = decode_jwt(token.credentials)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return user_id
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@app.post("/chat")
async def secure_chat(
    query: str,
    user_id: str = Depends(verify_token)
):
    """Secure chat endpoint with authentication"""
    
    result = await process_query(query, user_id)
    return result
```

---

## 4. Performance Optimization

### Connection Pooling

```python
from sqlalchemy.pool import QueuePool
from sqlalchemy import create_engine

# Configure connection pool
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  # Number of connections to maintain
    max_overflow=30,  # Additional connections allowed
    pool_timeout=30,  # Seconds to wait for connection
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True  # Verify connections before using
)
```

### Caching Strategy

```python
from functools import lru_cache
from redis import Redis
import json

# Redis cache for distributed caching
redis_cache = Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

def cache_key(query: str, user_id: str) -> str:
    """Generate cache key"""
    return f"rag:{user_id}:{hash(query)}"

async def cached_retrieval(state: RAGState) -> Dict[str, Any]:
    """Retrieval with caching"""
    
    query = state["query"]
    user_id = state["user_id"]
    key = cache_key(query, user_id)
    
    # Check cache
    cached = redis_cache.get(key)
    if cached:
        logger.info(f"Cache hit for query: {query[:50]}")
        return json.loads(cached)
    
    # Cache miss - perform retrieval
    docs = await hybrid_search(query, user_id)
    
    # Store in cache (5 minute TTL)
    result = {"retrieved_docs": docs}
    redis_cache.setex(key, 300, json.dumps(docs))
    
    return result
```

### Async Optimization

```python
import asyncio

async def parallel_processing(state: RAGState) -> Dict[str, Any]:
    """Process multiple operations in parallel"""
    
    query = state["query"]
    
    # Run operations in parallel
    tasks = [
        dense_search(query, state["user_id"]),
        bm25_search(query, state["user_id"]),
        query_expansion(query),
        user_context_load(state["user_id"])
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    dense_docs, bm25_docs, expanded_queries, user_context = results
    
    # Handle exceptions
    if isinstance(dense_docs, Exception):
        logger.error(f"Dense search failed: {dense_docs}")
        dense_docs = []
    
    return {
        "retrieved_docs": dense_docs + bm25_docs,
        "expanded_queries": expanded_queries,
        "user_context": user_context
    }
```

---

## 5. Observability and Alerting

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "K.I.R.A Agentic RAG - Production",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(agentic_rag_graph_executions_total[5m])"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(agentic_rag_graph_executions_total{status='error'}[5m])"
          }
        ]
      },
      {
        "title": "P95 Latency",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, agentic_rag_graph_duration_seconds)"
          }
        ]
      },
      {
        "title": "Agent Quality Scores",
        "targets": [
          {
            "expr": "agentic_rag_agent_quality_score"
          }
        ]
      }
    ]
  }
}
```

### Alert Rules

```yaml
# prometheus/alerts.yaml
groups:
  - name: agentic_rag_alerts
    rules:
      - alert: HighErrorRate
        expr: |
          rate(agentic_rag_graph_executions_total{status='error'}[5m]) 
          > 
          rate(agentic_rag_graph_executions_total[5m]) * 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in Agentic RAG"
          description: "Error rate is above 5% for 5 minutes"
      
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, agentic_rag_graph_duration_seconds) > 30
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High P95 latency in Agentic RAG"
          description: "P95 latency is above 30 seconds"
      
      - alert: LowQualityScores
        expr: |
          agentic_rag_agent_quality_score < 0.7
        for: 15m
        labels:
          severity: info
        annotations:
          summary: "Low quality scores detected"
          description: "Agent quality score below 0.7 for 15 minutes"
```

### Health Checks

```python
from fastapi import FastAPI
from sqlalchemy import text

app = FastAPI()

@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy"}

@app.get("/ready")
async def readiness_check():
    """Readiness check with dependencies"""
    
    checks = {
        "database": check_database(),
        "redis": check_redis(),
        "qdrant": check_qdrant(),
        "llm_api": check_llm_api()
    }
    
    all_healthy = all(checks.values())
    
    return {
        "ready": all_healthy,
        "checks": checks
    }

async def check_database() -> bool:
    """Check database connectivity"""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

async def check_redis() -> bool:
    """Check Redis connectivity"""
    try:
        redis_cache.ping()
        return True
    except Exception:
        return False
```

---

## 6. Production Rollout Strategy

### Feature Flag Rollout

```python
from src.agentic_rag.integration.feature_flags import AgenticRAGRolloutStrategy

# Initialize rollout strategy
rollout = AgenticRAGRolloutStrategy()

# Phase 1: Internal testing (0%)
rollout.rollout_phase_1()  # 0% rollout

# Phase 2: Beta rollout (5%)
rollout.rollout_phase_2(percentage=5)

# Phase 3: Gradual rollout (25% → 50%)
rollout.rollout_phase_3(percentage=25)
# Monitor metrics
# If OK: rollout.rollout_phase_3(percentage=50)

# Phase 4: Full rollout (100%)
rollout.rollout_phase_4()
```

### A/B Testing Setup

```python
import random

def should_use_agentic_rag(user_id: str) -> bool:
    """Determine if user should get Agentic RAG (A/B test)"""
    
    # Get test configuration
    test_percentage = os.getenv("AGENTIC_RAG_TEST_PERCENTAGE", "10")
    test_percentage = int(test_percentage)
    
    # Hash user ID for consistent assignment
    user_hash = hash(user_id) % 100
    
    return user_hash < test_percentage

# In handler
async def handle_query(query: str, user_id: str):
    """Handle query with A/B test routing"""
    
    if should_use_agentic_rag(user_id):
        # Use Agentic RAG
        return await agentic_rag_handler.handle(query, user_id)
    else:
        # Use legacy RAG (control)
        return await legacy_rag_handler.handle(query, user_id)
```

### Monitoring During Rollout

```python
# Track A/B test metrics
from prometheus_client import Counter

agentic_requests = Counter('ab_test_agentic_requests_total', 'Agentic RAG requests')
legacy_requests = Counter('ab_test_legacy_requests_total', 'Legacy RAG requests')

async def track_request(handler_type: str):
    """Track A/B test request"""
    if handler_type == "agentic":
        agentic_requests.inc()
    else:
        legacy_requests.inc()
```

---

## 7. Best Practices

### Code Organization

```python
# Recommended project structure
src/
├── agentic_rag/
│   ├── __init__.py
│   ├── schemas.py          # State and config schemas
│   ├── graph/
│   │   ├── __init__.py
│   │   └── agentic_rag_graph.py  # Main graph
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── retrieval_agent.py
│   │   ├── generation_agent.py
│   │   └── critique_agent.py
│   └── integration/
│       ├── __init__.py
│       ├── agentic_rag_handler.py
│       └── feature_flags.py
├── monitoring/
│   ├── metrics.py          # Prometheus metrics
│   └── logging.py          # Structured logging
└── main.py                 # FastAPI app
```

### Error Handling

```python
# Always use try/except in nodes
async def safe_node(state: RAGState) -> Dict[str, Any]:
    try:
        result = await node_logic(state)
        return result
    except SpecificError as e:
        logger.error(f"Known error: {e}")
        return {"error": str(e), "status": "error"}
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise
```

### Testing

```python
# Unit tests for nodes
@pytest.mark.asyncio
async def test_retrieval_agent():
    state = {
        "query": "test query",
        "user_id": "test-user"
    }
    
    result = await retrieval_agent(state)
    
    assert "retrieved_docs" in result
    assert len(result["retrieved_docs"]) > 0

# Integration tests for graph
@pytest.mark.asyncio
async def test_agentic_rag_graph():
    graph = create_agentic_rag_graph()
    
    result = await graph.ainvoke({
        "query": "test query",
        "user_id": "test-user"
    })
    
    assert "final_response" in result
    assert "final_citations" in result
```

---

## 8. Q&A and Planning

### Preparation for Phase 1

**Questions to discuss:**

1. **Skills Assessment**
   - Do team members feel comfortable with LangGraph?
   - Any areas that need more training?
   - Ready for Phase 1 implementation?

2. **Infrastructure Setup**
   - Do we have all required services?
   - Are monitoring tools configured?
   - Is CI/CD ready for LangGraph apps?

3. **Implementation Planning**
   - Who will work on which agents?
   - What is the timeline for Phase 1?
   - How will we coordinate work?

4. **Risk Mitigation**
   - What are our biggest concerns?
   - How will we handle blockers?
   - What is our fallback plan?

### Next Steps

1. **Complete Training Assessment** (30 min)
   - Take final quiz
   - Complete self-assessment
   - Discuss any gaps

2. **Setup Development Environment** (1 hour)
   - Install all dependencies
   - Configure monitoring tools
   - Test LangGraph basics

3. **Review Phase 1 Plan** (1 hour)
   - Read Phase 1 documentation
   - Assign tasks to team members
   - Set up timeline

4. **Begin Phase 1 Implementation** (starting Week 2)
   - Install LangGraph infrastructure
   - Implement 4-agent foundation
   - Build basic graph for testing

---

## Resources

### Production Deployment
- [LangGraph Deployment Guide](https://langchain-ai.github.io/langgraph/concepts/low_level/#deployment)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [Docker Optimization](https://docs.docker.com/develop/dev-best-practices/)

### Monitoring
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- [LangSmith Tracing](https://smith.langchain.com/)

### Security
- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Security](https://python.readthedocs.io/en/stable/library/security_warnings.html)

---

## Key Takeaways

1. ✅ **Monitor everything**: Use LangSmith, Prometheus, and structured logging
2. ✅ **Secure by default**: Validate inputs, use authentication, rate limiting
3. ✅ **Optimize performance**: Cache, parallel execution, connection pooling
4. ✅ **Prepare for production**: Health checks, alerting, gradual rollout
5. ✅ **Test thoroughly**: Unit tests, integration tests, load tests
6. ✅ **Document everything**: Architecture, deployment, runbooks

---

**Training Duration**: 4 hours  
**Q&A Duration**: 1 hour  
**Planning Duration**: 1 hour

---

**Last Updated**: 2025-06-10  
**Maintainer**: Backend Lead  
**Next**: Phase 1 Implementation (Week 2)

---

## Appendix: Training Completion Checklist

### Individual Checklist

- [ ] Completed all 4 days of training
- [ ] Passed all quizzes (80%+ score)
- [ ] Built working 2-node graph
- [ ] Built working 3-node graph with conditional routing
- [ ] Implemented error handling
- [ ] Implemented retry logic
- [ ] Understood streaming support
- [ ] Reviewed monitoring setup
- [ ] Reviewed security best practices
- [ ] Ready for Phase 1 implementation

### Team Checklist

- [ ] All team members completed training
- [ ] Development environments setup
- [ ] Monitoring tools configured
- [ ] CI/CD pipeline ready
- [ ] Phase 1 tasks assigned
- [ ] Timeline established
- [ ] Risk mitigation plan in place
- [ ] Ready to start Phase 1
