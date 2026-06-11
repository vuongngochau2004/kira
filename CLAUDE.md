# CLAUDE.md - Development Guidelines

## Project Overview

**K.I.R.A Simplified** is a production-ready RAG (Retrieval-Augmented Generation) system with multi-stage query routing, hybrid retrieval, and intelligent OCR fallback. This document provides context for AI assistants working on this codebase.

## Current Architecture

### System Overview

The system follows a **Pragmatic Hexagonal Architecture (Ports & Adapters)** combined with a **Modular Monolith** pattern:

```mermaid
graph TB
    subgraph Serving["SERVING Layer (src/server/)"]
        FastAPI[FastAPI Server]
        AuthJWT[JWT Auth Middleware]
        Endpoints[API Routers: Auth, Chat, Doc, Eval, Metrics]
    end

    subgraph Core["APPLICATION CORE (src/modules/)"]
        subgraph ChatModule["modules/chat/"]
            ConversationalHandler[ConversationalHandler]
            RAGHandler[RAGHandler]
        end

        subgraph RAGModule["modules/rag/"]
            Orchestrator[OrchestratorAgent]
            RetrievalAgent[RetrievalAgent]
            GenerationAgent[GenerationAgent]
            QualityAgent[QualityAgent]
            LangGraph[LangGraph Pipeline]
        end
        
        subgraph ClassifyModule["modules/classification/"]
            Classifier[CompositeClassifier]
            Strategies[Keyword/Cache/LLM]
        end

        subgraph DocModule["modules/document/"]
            Pipeline[Ingestion Pipeline]
            Extractor[Text Extraction]
        end

        subgraph RetrievalModule["modules/retrieval/"]
            HybridRetrieval[Hybrid Search / RRF]
        end

        subgraph EvalModule["modules/evaluation/"]
            RagasService[RAGAS Evaluation]
        end
    end

    subgraph Ports["PORTS (src/shared/ports/)"]
        LLMPort[LLMPort]
        VectorStorePort[VectorStorePort]
        EmbeddingPort[EmbeddingPort]
        StoragePort[StoragePort]
        OCRPort[OCRPort]
    end

    subgraph Adapters["ADAPTERS (src/shared/adapters/)"]
        GLMAdapter[GLMAdapter]
        QdrantAdapter[QdrantAdapter]
        EmbeddingAPIAdapter[EmbeddingAPIAdapter]
        MinIOAdapter[MinIOAdapter]
        PaddleOCRAdapter[PaddleOCRAdapter]
    end

    subgraph Infra["SHARED INFRASTRUCTURE (src/shared/)"]
        subgraph Database["Persistence & Shared Domain"]
            PG[(PostgreSQL)]
            SharedEntities[User, Doc, Citation VO]
        end
        subgraph Kernel["Kernel & DI"]
            DI[ServiceContainer & Registry]
        end
    end

    Serving --> Core
    Core --> Ports
    Ports <|.. Adapters
    Adapters --> Serving
    Core -.->|uses DI from| Kernel
    Core -.->|uses DB models from| Database
```

### Architecture Principles

1. **Modular Monolith**: Core business functionality is organized into bounded context directories inside `src/modules/`. Modules communicate via clean application interfaces or the shared kernel.
2. **Ports & Adapters (Hexagonal)**: All external systems (LLM providers, databases, storage engines, OCR engines) are defined as abstract contracts (**Ports**) in `src/shared/ports/`. Concretions (**Adapters**) in `src/shared/adapters/` implement these ports, allowing simple mocking and hot-swapping.
3. **Dependency Injection**: A global `ServiceRegistry` compiles and registers adapters into the `ServiceContainer` on server initialization, decoupling composition from execution.
4. **SOLID Principles**: Focused on dependency inversion (depending on Port ABCs rather than adapters), single responsibility (separate handlers, agents, and strategies), and open-closed extension.

### Module Structure

```
src/
├── server/                    # SERVING Layer
│   ├── main.py                # FastAPI app & initialization
│   └── api/                   # API routers (v1) & middlewares
│
├── modules/                   # APPLICATION CORE (Modular Monolith Contexts)
│   ├── chat/                  # Chat Context: conversational/RAG handlers, usecases, prompts
│   ├── rag/                   # RAG Context: agent orchestrators, langgraph workflows, prompts, state
│   ├── classification/        # Classification Context: CompositeClassifier & routing strategies
│   ├── document/              # Document Context: ETL ingestion pipelines, chunkers, upload usecases
│   ├── retrieval/             # Retrieval Context: hybrid search, retrievers (dense, BM25)
│   └── evaluation/            # Evaluation Context: RAGAS services, golden datasets
│
├── shared/                    # EXTERNAL & CROSS-CUTTING Layer
│   ├── ports/                 # Hexagonal Ports (LLMPort, VectorStorePort, EmbeddingPort, etc.)
│   ├── adapters/              # Concrete Adapters (GLMAdapter, QdrantAdapter, MinIOAdapter, etc.)
│   ├── infrastructure/        # Shared infra clients (auth, monitoring/metrics, persistence/database, llm)
│   ├── domain/                # Shared domain entities & value objects (User, Document, Citation VO)
│   └── kernel/                # Shared kernel DI container, feature flags, base interfaces
│
├── models/                    # Shared Pydantic request/response schemas
└── constants/, config/        # Global constants and settings validation
```

## Development Standards

### PEP 8 Compliance

All Python code **MUST** follow [PEP 8](https://peps.python.org/pep-0008/) style guide.

#### Indentation & Spacing
- Use **4 spaces** per indentation level (NO tabs)
- Maximum line length: **100 characters** (soft), **120 characters** (hard)
- **2 blank lines** between top-level definitions
- **1 blank line** between methods in classes

#### Imports
```python
# ✅ CORRECT - Grouped by type with blank lines
import os
import sys

from typing import Optional, List

from fastapi import Depends
from langchain.tools import tool

from src.modules.chat.infrastructure.handlers.rag_handler import RAGHandler
from src.shared.kernel.interfaces.classification import Intent

# ❌ WRONG
import os, sys
from src.handlers import *
from .module import SomeClass  # Use absolute imports
```

#### Naming Conventions
```python
# ✅ CORRECT
class DocumentProcessor:         # CapWords for classes
    MAX_CHUNK_SIZE = 1000         # UPPER_SNAKE_CASE for constants
    
    def __init__(self, config: dict):
        self._config = config      # Leading underscore for private
    
    def process_document(self, doc_id: str) -> dict:  # snake_case for methods
        """Process document and return metadata."""
        return self._internal_process(doc_id)
    
    def _internal_process(self, doc_id: str) -> dict:  # Private method
        pass

# ❌ WRONG
class documentProcessor:          # Wrong class naming
    max_chunk_size = 1000          # Wrong constant naming
```

#### Type Hints (Required)
```python
# ✅ CORRECT - Python 3.10+
from typing import AsyncIterator

async def handle_stream(
    query: str,
    user_id: str | UUID,
    classification: ClassificationResult,
    context: dict | None = None
) -> AsyncIterator[dict]:
    """Stream response chunks."""
    yield {"type": "content", "data": {"text": "Response..."}}
```

#### Docstrings (Google Style)
```python
# ✅ CORRECT
def classify_query(query: str, user_id: str) -> ClassificationResult:
    """
    Classify a user query into intent categories.
    
    Args:
        query: The user's search query
        user_id: Unique identifier for the user
    
    Returns:
        ClassificationResult containing intent and confidence score
    
    Raises:
        ValueError: If query is empty or user_id is invalid
    """
    if not query:
        raise ValueError("Query cannot be empty")
    return ClassificationResult(intent=Intent.RAG, confidence=0.95)
```

#### Class Structure Order
1. Class docstring
2. Class attributes (constants)
3. `__init__` method
4. Public instance methods
5. Private methods (starting with `_`)
6. Dunder methods (`__str__`, `__repr__`, etc.)

```python
# ✅ CORRECT
class QueryHandler:
    """
    Base class for query handlers.
    
    Provides common functionality for all handler implementations.
    """
    
    MAX_RETRIES = 3
    DEFAULT_TIMEOUT = 30.0
    
    def __init__(self, config: HandlerConfig):
        """Initialize handler with configuration."""
        self.config = config
    
    async def handle(self, query: str) -> HandlerResult:
        """Handle query and return result."""
        pass
    
    def _validate_query(self, query: str) -> bool:
        """Private validation method."""
        return len(query.strip()) > 0
```

#### Async/Await
```python
# ✅ CORRECT
async def process_document(doc_id: str) -> dict:
    """Process document asynchronously."""
    doc = await db.get_document(doc_id)
    chunks = await chunker.chunk(doc.content)
    return {"doc_id": doc_id, "chunks": len(chunks)}

# ❌ WRONG
async def process_document(doc_id: str) -> dict:
    doc = db.get_document(doc_id)  # Missing await!
    return {"doc_id": doc_id}
```

#### Linting Tools
```bash
# Install
pip install black isort flake8 pylint mypy

# Format
black src/
isort src/

# Lint
flake8 src/ --max-line-length=120
mypy src/ --strict
```

### File Naming Conventions

- Use **snake_case** for Python files: `document_store.py`, `paddleocr_client.py`
- This makes files self-documenting for LLM tools (Grep, Glob, Search)
- **DO NOT** use camelCase for Python files

### When Adding New Features

#### New Handler? Add to `src/modules/chat/infrastructure/handlers/` (or create a new module in `src/modules/`)
```python
from src.shared.kernel.interfaces.handlers import QueryHandlerBase, HandlerResult
from src.shared.kernel.interfaces.classification import ClassificationResult

class MyHandler(QueryHandlerBase):
    """My custom handler implementation."""
    
    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict | None = None
    ) -> HandlerResult:
        # Execute query logic (NO classification logic here!)
        return HandlerResult(content="Response...", metadata={})
```

#### New Classification Strategy? Add to `src/modules/classification/domain/strategies/`
```python
from src.shared.kernel.interfaces.classification import ClassificationStrategyBase

class MyStrategy(ClassificationStrategyBase):
    """My custom classification strategy."""
    
    async def classify(self, query: str, user_id: str | UUID) -> ClassificationResult:
        # Return classification result
        return ClassificationResult(intent=Intent.RAG, confidence=0.95)
```

#### New Tool? Add to `src/tools/`
```python
from langchain.tools import tool

@tool
async def my_tool(input: str) -> str:
    """
    Tool description for LangChain.
    
    Args:
        input: Input parameter description
    
    Returns:
        Output description
    """
    return "Result"
```

#### New Endpoint? Add to `src/server/api/v1/`
```python
from fastapi import APIRouter, Depends
from src.shared.infrastructure.auth.dependencies import get_current_user

router = APIRouter()

@router.post("/my-endpoint")
async def my_endpoint(
    data: MySchema,
    current_user: User = Depends(get_current_user)
):
    """Endpoint description."""
    return {"result": "success"}
```

### Testing

- Tests located in `tests/`
- Use pytest with async support
- Test with real database (docker-compose services)
- Mock external API calls (LLM, embedding, OCR)

### Error Handling

```python
# ✅ CORRECT - Specific exceptions with context
try:
    result = await api_call(data)
except (ConnectionError, TimeoutError) as e:
    logger.error(f"API call failed: {e}")
    raise QueryProcessingError(f"Unable to process query: {e}") from e
finally:
    await close_connection()

# ❌ WRONG - Bare except
try:
    result = await api_call(data)
except:
    pass
```

## API Reference

### SSE Streaming Format

```json
// Routing decision
{"type": "routing", "data": {"router": "RAGRouter", "intent": "rag", "confidence": 0.95}}

// Retrieval progress
{"type": "retrieval", "data": {"iteration": 1, "strategy": "hybrid", "docs_retrieved": 5}}

// Content chunks
{"type": "content", "data": {"text": "Response chunk..."}}

// Final metadata
{"type": "metadata", "data": {"status": "success", "citations": [...], "conversation_id": "..."}}

// Done signal
{"type": "done"}
```

### Standard Response Format

```json
{
  "content": "Answer text...",
  "citations": [{"filename": "doc.pdf", "page": 1, "text": "..."}],
  "conversation_id": "uuid",
  "message_id": "uuid",
  "metadata": {"router": "RAGRouter", "agent": "rag", "latency_ms": 1234}
}
```

## Environment Configuration

### Required Environment Variables

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USER=kira
POSTGRES_PASSWORD=kira_secret
POSTGRES_DB=kira_dev

# JWT
JWT_SECRET_KEY=your-secret-key-here

# LLM
LLM_PROVIDER=glm
GLM_API_KEY=your-glm-api-key

# Embedding
EMBEDDING_BASE_URL=http://your-embedding-api:8888

# OCR (optional)
OCR_ENABLED=true
OCR_BASE_URL=http://paddleocr-service:8868
```

### Configuration Priority

1. **Static config** (`config/settings.yaml`) - Chunking, retrieval parameters
2. **Environment variables** (`.env`) - Secrets, API keys, URLs
3. **Settings class** (`config/config.py`) - Pydantic validation

## Common Tasks

### Adding a New LLM Provider

1. Add configuration to `config/config.py`
2. Create adapter in `src/shared/adapters/llm/` and implement `LLMPort`
3. Wire the new adapter in the ServiceRegistry (`src/shared/kernel/di/registry.py`)
4. Update `LLM_PROVIDER` in `.env`

### Modifying Retrieval Strategy

1. Update `config/settings.yaml` for parameters
2. Modify retrieval logic in `src/modules/retrieval/`
3. Test with different query types

### Database Migration

1. Update `src/shared/infrastructure/persistence/database/models.py` (SQLAlchemy model)
2. Update `src/models/*.py` (Pydantic schemas)
3. Create Alembic migration

## Vietnamese Language Support

The system is optimized for Vietnamese:

- **Embeddings**: BAAI/bge-m3 or Vietnamese-embedding-v2
- **OCR**: PaddleOCR with Vietnamese language model
- **LLM**: GLM-4.5 (Zhipu AI) with strong Vietnamese support
- **Text Cleaning**: Preserves Vietnamese diacritics

## Frontend Notes

Separate Next.js 16 application:

- Located in `frontend/`
- Uses shadcn/ui components
- Zustand for state management
- TanStack Query for API calls
- i18n support (Vietnamese/English)
- **Port**: 3001

## Deployment

### Infrastructure

All infrastructure runs in Docker Compose:

- PostgreSQL 16 with pgvector
- Qdrant vector database
- MinIO object storage

### Production Checklist

- Set `APP_ENV=production`
- Use strong `JWT_SECRET_KEY`
- Configure CORS origins
- Enable `AUTH_ENABLED=true`
- Set up PaddleOCR service (if using OCR)
- Configure external LLM and embedding APIs

## Troubleshooting

### Common Issues

1. **BM25 index empty**: Check BM25 builder initialization
2. **OCR not working**: Verify `OCR_BASE_URL` and service health
3. **No retrieval results**: Check Qdrant collection, verify embeddings
4. **Auth errors**: Verify JWT token, check `AUTH_ENABLED` setting

### Debug Mode

Set `DEBUG=true` in `.env` for detailed logging.

## Resources

- **Architecture**: 4-layer pattern + SOLID principles
- **Hybrid Retrieval**: RRF (Reciprocal Rank Fusion) algorithm
- **OCR**: PaddleOCR HTTP API
- **Vector DB**: Qdrant documentation
- **Frontend**: Next.js 16 + shadcn/ui
- **PEP 8**: [Official Style Guide](https://peps.python.org/pep-0008/)

---

*Last Updated: 2026-06-11*
*This document is maintained alongside the codebase. Update when architecture or patterns change.*
