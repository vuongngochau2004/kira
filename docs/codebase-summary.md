# Tóm tắt Codebase

## Tổng quan

K.I.R.A Simplified là một RAG (Retrieval-Augmented Generation) system production-ready với:
- **Backend**: Python 3.12+, FastAPI, LangChain
- **Frontend**: Next.js 16, shadcn/ui, Zustand
- **Architecture**: 4-layer pattern với SOLID refactor (Protocol-based design → ABC migration)

## Cấu trúc Backend

```
src/
├── api/                    # SERVING LAYER - HTTP endpoints
│   ├── dependencies.py     # FastAPI dependencies
│   ├── routes/             # API route modules
│   │   ├── auth.py         # Authentication endpoints
│   │   ├── chat.py         # Chat/streaming endpoints
│   │   ├── documents.py    # Document management
│   │   └── health.py       # Health check
│   └── main.py             # FastAPI app initialization
│
├── agents/                 # AGENT LAYER - Routing & LLM logic
│   ├── llm.py             # LLM client (GLM/Claude/GPT)
│   ├── prompts.py         # Prompt templates
│   ├── rag_agent.py       # AgenticRAG implementation
│   └── routers/           # Router implementations (legacy)
│       ├── base.py        # BaseRouter ABC
│       ├── rag_router.py  # RAGRouter
│       ├── conv_router.py # ConversationalRouter
│       └── registry.py    # RouterRegistry
│
├── tools/                 # LangChain tools for agent integration
│   ├── retrieval_tools.py # Document retrieval tools
│   └── ingestion_tools.py # Document ingestion tools
│
├── interfaces/            # ABC definitions (SOLID refactor) ✅ Complete
│   ├── classification.py  # ClassificationStrategyBase, Intent, ClassificationResult
│   ├── handlers.py        # QueryHandlerBase, HandlerResult, Citation
│   ├── retrieval.py      # RetrieverBase, Document ABCs
│   └── container.py       # DependencyContainerBase, Lifecycle
│
├── classification/        # Query intent detection (Strategy pattern)
│   ├── strategies/        # Classification implementations
│   │   ├── keyword.py     # Fast keyword-based classifier (<5ms)
│   │   ├── cached.py      # LRU cache wrapper
│   │   ├── llm.py         # LLM-based classifier (~800ms)
│   │   └── composite.py   # CompositeClassifier with fallback chain
│   └── cache/             # LRU cache implementation
│
├── handlers/             # Query execution handlers (SRP compliance)
│   ├── rag.py             # RAGHandler: retrieval + LLM generation
│   ├── conversational.py  # ConversationalHandler: direct LLM chat
│   └── adapters/         # Adapter pattern for backward compatibility
│       └── router_adapter.py  # Adapts old routers to new handlers
│
├── di/                   # Dependency injection (DIP compliance)
│   ├── container.py       # ServiceContainer with lifecycle management
│   ├── registry.py        # ServiceRegistry for service registration
│   └── feature_flags.py  # FeatureFlagManager with percentage rollout
│
├── retrieval/            # RETRIEVAL LAYER - Search algorithms
│   ├── dense.py          # Vector similarity search (Qdrant)
│   ├── bm25.py           # BM25 keyword search
│   └── hybrid.py         # RRF fusion strategy
│
├── indexing/            # INDEXING LAYER - Database clients
│   ├── qdrant_store.py   # Qdrant client
│   ├── document_store.py # PostgreSQL metadata
│   └── file_store.py     # MinIO object storage
│
├── ingestion/            # INGESTION LAYER - ETL pipeline
│   ├── extractor.py       # Text extraction + OCR fallback
│   ├── paddleocr_client.py # PaddleOCR HTTP client
│   ├── cleaner.py        # Text normalization
│   ├── chunker.py        # Document chunking
│   ├── embedding.py      # Embedding generation
│   ├── bm25_builder.py   # BM25 index builder
│   └── pipelines.py      # Ingestion orchestration
│
├── auth/                 # JWT authentication
│   ├── jwt_handler.py   # JWT token management
│   └── password.py       # Password hashing
│
├── database/            # SQLAlchemy models
│   ├── base.py          # Base model and session
│   ├── models.py        # ORM models (User, Document, Conversation, etc.)
│   └── connection.py    # Database connection setup
│
├── models/              # Pydantic schemas
│   ├── auth.py          # Auth-related schemas
│   ├── chat.py          # Chat request/response schemas
│   ├── document.py      # Document schemas
│   └── schemas.py       # Common schemas
│
├── constants/           # Application constants
│   ├── __init__.py      # Error messages, constants
│   └── prompts.py       # Prompt templates
│
└── main.py              # FastAPI entry point
```

## Cấu trúc Frontend

```
frontend/src/
├── app/                 # Next.js App Router
│   ├── (auth)/         # Auth group layout
│   │   ├── login/
│   │   └── register/
│   ├── chat/           # Chat interface
│   ├── documents/      # Document management
│   └── layout.tsx      # Root layout
│
├── components/         # UI components
│   ├── auth/          # Auth components
│   ├── common/        # Shared components
│   ├── documents/     # Document-related components
│   ├── chat/          # Chat components
│   └── sidebar/       # Sidebar navigation
│
├── lib/               # Utilities and core logic
│   ├── api/          # API clients
│   ├── hooks/        # Custom React hooks
│   ├── stores/       # Zustand stores
│   └── utils/        # Helper functions
│
└── ...
```

## Các Module Chính

### 1. Query Routing (Multi-Stage)

**Location**: `src/classification/`, `src/handlers/`

**Flow**:
1. **Quick Filter** (`KeywordStrategy`): Fuzzy filename + keyword matching (<5ms)
2. **LLM Classification** (`LLMStrategy`): Intent detection (~800ms)
3. **Handler Dispatch**: Route to appropriate handler

**Key Classes**:
- `CompositeClassifier`: Chains strategies with fallback
- `RAGHandler`: Document retrieval + generation
- `ConversationalHandler`: Direct LLM chat

### 2. Hybrid Retrieval

**Location**: `src/retrieval/`

**Components**:
- `DenseRetrieval`: Vector search via Qdrant
- `BM25Retrieval`: Keyword search per-user index
- `HybridRetrieval`: RRF fusion

**Key Features**:
- Parallel retrieval from both sources
- Reciprocal Rank Fusion for result merging
- Per-user document filtering

### 3. Document Ingestion

**Location**: `src/ingestion/`

**Pipeline**:
```
Upload → MinIO Storage
   ↓
Extract (PyMuPDF → PaddleOCR fallback)
   ↓
Clean (Vietnamese-preserving normalization)
   ↓
Chunk (configurable size + overlap)
   ↓
Embed (Vietnamese embedding API)
   ↓
Index (Qdrant + BM25 + PostgreSQL)
```

**Key Classes**:
- `Extractor`: Text extraction with OCR fallback
- `PaddleOCRClient`: HTTP client for OCR service
- `Chunker`: Document chunking strategies
- `BM25Builder`: Per-user BM25 index management

### 4. LLM Integration

**Location**: `src/agents/llm.py`

**Providers**:
- GLM-4.5 (Zhipu AI) - Primary
- Anthropic Claude - Fallback
- OpenAI GPT - Fallback

**Features**:
- Streaming responses
- Citation generation
- Multi-provider support

### 5. Dependency Injection

**Location**: `src/di/`

**Components**:
- `ServiceContainer`: Protocol-based DI container
- `ServiceRegistry`: Centralized service registration
- `FeatureFlagManager`: Percentage-based feature rollout

**Lifecycle Management**:
- SINGLETON: One instance per app lifetime
- TRANSIENT: New instance each time
- SCOPED: One instance per scope

## Data Flow

### Chat Request Flow

```
User Query → FastAPI (/chat/stream)
    ↓
JWT Authentication
    ↓
CompositeClassifier.classify()
    ↓ (fallback chain)
  KeywordStrategy → CachedStrategy → LLMStrategy
    ↓
ServiceContainer.get(QueryHandlerBase)
    ↓
RAGHandler.handle_stream() or ConversationalHandler.handle_stream()
    ↓
HybridRetrieval.search() (Dense + BM25 → RRF)
    ↓
LLMClient.generate() with streaming
    ↓
SSE Events (routing → retrieval → content → metadata → done)
    ↓
Frontend displays streaming response
```

### Document Upload Flow

```
File Upload → FastAPI (/documents)
    ↓
MinIO Storage (raw file)
    ↓
Background Task: ingestion_pipeline()
    ↓
Extractor.extract() (PyMuPDF → PaddleOCR)
    ↓
Cleaner.clean() (Vietnamese-preserving)
    ↓
Chunker.chunk() (configurable)
    ↓
Parallel: Embedding.generate() + BM25Builder.add()
    ↓
QdrantStore.upsert() + PostgreSQL.save()
    ↓
Document status: PROCESSING → COMPLETED
```

## Integration Points

### External Services

1. **Qdrant Vector Database**
   - Client: `src/indexing/qdrant_store.py`
   - Usage: Vector storage and similarity search

2. **PostgreSQL + pgvector**
   - Client: SQLAlchemy (`src/database/`)
   - Usage: Metadata, user data, conversations

3. **MinIO Object Storage**
   - Client: `src/indexing/file_store.py`
   - Usage: File storage (PDFs, images)

4. **LLM APIs**
   - Client: `src/agents/llm.py`
   - Usage: Text generation, classification

5. **Embedding API**
   - Client: `src/ingestion/embedding.py`
   - Usage: Vector embeddings for chunks

6. **PaddleOCR Service** (Optional)
   - Client: `src/ingestion/paddleocr_client.py`
   - Usage: OCR for scanned PDFs

### Internal Communication

1. **FastAPI → Handlers**
   - Via `ServiceContainer` DI
   - Protocol-based resolution

2. **Handler → Retrieval**
   - Direct method calls
   - Async/await pattern

3. **Handler → LLM**
   - Streaming interface
   - Structured chunks (routing, retrieval, content, metadata)

## Code Organization Principles

### 1. Layer Separation

- **SERVING** (`src/api/`): HTTP concerns only
- **AGENT/TOOLS** (`src/agents/`, `src/tools/`): Business logic
- **RETRIEVAL** (`src/retrieval/`, `src/indexing/`): Data access
- **INGESTION** (`src/ingestion/`): ETL pipeline

### 2. Protocol-Based Design

- High-level modules depend on ABCs, not concretions (DIP)
- All interfaces defined in `src/interfaces/`
- Enables easy testing and swapping implementations

### 3. Per-User Isolation

- BM25 indexes scoped to `user_id`
- Document filtering by `user_id`
- Conversations scoped to `user_id`

### 4. Async-First

- All I/O operations use async/await
- Database queries async
- External API calls async

### 5. Naming Conventions

- Python: `snake_case` for files, `PascalCase` for classes
- TypeScript: `kebab-case` for files, `PascalCase` for components
- Descriptive names preferred over brevity

## Tech Stack Details

### Backend

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.12+ |
| Framework | FastAPI 0.104+ |
| LLM Orchestration | LangChain Core |
| ORM | SQLAlchemy 2.0 |
| Vector DB | Qdrant Client |
| Authentication | JWT (python-jose) |
| Validation | Pydantic v2 |

### Frontend

| Component | Technology |
|-----------|-----------|
| Framework | Next.js 16 (App Router) |
| Styling | Tailwind CSS |
| Components | shadcn/ui (Radix UI) |
| State | Zustand |
| Data Fetching | TanStack Query |
| i18n | next-intl |

### Infrastructure

| Component | Technology |
|-----------|-----------|
| Database | PostgreSQL 16 + pgvector |
| Vector DB | Qdrant |
| Object Storage | MinIO |
| Containerization | Docker Compose |

## Key Files Reference

| File | Purpose |
|------|---------|
| `src/main.py` | FastAPI entry point |
| `src/di/container.py` | Dependency injection setup |
| `src/classification/strategies/composite.py` | Classification chain |
| `src/handlers/rag.py` | RAG execution |
| `src/retrieval/hybrid.py` | RRF fusion |
| `src/ingestion/pipelines.py` | Ingestion orchestration |
| `config/config.py` | Configuration management |
| `CLAUDE.md` | Development guidelines |

## Related Documentation

- [Tổng quan Dự án](./project-overview.md) - Project overview
- [Kiến trúc Hệ thống](./system-architecture.md) - Detailed architecture
- [Tiêu chuẩn Code](./code-standards.md) - Code conventions
- [Lộ trình Phát triển](./project-roadmap.md) - Development roadmap
- [CLAUDE.md](../CLAUDE.md) - Detailed development guidelines
