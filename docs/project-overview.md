# Tổng quan Dự án

## Thông tin Project

- **Tên**: K.I.R.A Simplified
- **Mô tả**: Knowledge-based Intelligent Retrieval Assistant - Production-ready RAG system with Hexagonal Modular Monolith Architecture
- **Loại**: Backend API + Frontend Web (Full-stack)
- **Giai đoạn**: Production-ready with Hexagonal Architecture Migration (Complete)
- **Version**: 1.0.0

## Tech Stack

### Backend
- **Runtime**: Python 3.12+
- **Framework**: FastAPI
- **Architecture**: Hexagonal Modular Monolith
  - Modules: chat, classification, document, evaluation, rag, retrieval
  - Shared Layer: ports, adapters, infrastructure, kernel, domain
  - Serving Layer: server with API v1 endpoints
- **LLM**: GLM-4.5 (Zhipu AI), Anthropic Claude, OpenAI GPT
- **LangGraph**: Multi-agent RAG orchestration

### Frontend
- **Framework**: Next.js 16 (App Router)
- **UI Library**: React 19
- **Styling**: Tailwind CSS, shadcn/ui (Radix UI)
- **State Management**: Zustand
- **Data Fetching**: TanStack Query
- **i18n**: next-intl (Vietnamese, English)

### Database
- **PostgreSQL**: 16 + pgvector extension
- **Vector DB**: Qdrant (1024-dim vectors)
- **Object Storage**: MinIO
- **Search**: Hybrid (Dense + BM25 with RRF)

### Development
- **Testing**: Pytest, pytest-asyncio, pytest-cov
- **Linting**: Ruff, MyPy
- **Build**: Docker Compose

## Core Capabilities

### 1. Multi-User Document Management
- PDF/DOCX/PPTX/TXT upload support
- Per-user document isolation
- Background ingestion pipeline
- Intelligent OCR fallback (PyMuPDF → PaddleOCR)
- Vietnamese text preservation

### 2. Hybrid Retrieval System
- **Dense Retrieval**: Vector similarity search via Qdrant
- **Keyword Retrieval**: BM25 per-user indexes
- **RRF Fusion**: Reciprocal Rank Fusion for result merging
- **Optional Reranking**: LLM-based document reranking
- **Citation Generation**: With verification and grounding

### 3. Intelligent Query Classification
- **Strategy Pattern**: Pluggable classification strategies
- **Fallback Chain**: Keyword → Cached → LLM
- **Intent Detection**: RAG vs Conversational routing
- **LRU Cache**: Performance optimization

### 4. Agentic RAG
- **LangGraph Integration**: Multi-agent orchestration
- **Thinking Visualization**: Claude-style thinking display
- **Citation Verification**: Grounding checks
- **Context Building**: Intelligent context assembly

### 5. Streaming Chat Experience
- **SSE Streaming**: Real-time response chunks
- **Structured Events**: routing, retrieval, thinking, content, citations
- **Conversation Persistence**: With soft delete
- **Multi-turn Context**: Message history management

### 6. Evaluation System
- **RAGAS Integration**: Faithfulness, relevancy, precision, recall
- **Golden Datasets**: Custom evaluation datasets
- **Batch Evaluation**: Efficient batch processing
- **Caching**: Evaluation result caching

### 7. Authentication & Security
- **JWT Authentication**: With httpOnly cookies
- **Per-User Isolation**: All data scoped by user_id
- **Soft Delete**: Conversations marked with deleted_at
- **CORS**: Configurable allowed origins

## Architecture Highlights

### Hexagonal Modular Monolith

```text
src/
├── server/                   # Serving Layer - HTTP only
│   ├── main.py              # FastAPI app
│   └── api/v1/              # API endpoints
│       ├── auth/
│       ├── chat/
│       ├── documents/
│       ├── evaluation/
│       └── metrics/
├── modules/                 # Application Modules
│   ├── chat/                # Chat use cases
│   ├── classification/      # Query routing
│   ├── document/            # Document management
│   ├── evaluation/          # RAGAS evaluation
│   ├── rag/                 # Agentic RAG
│   └── retrieval/           # Hybrid retrieval
├── shared/                  # Shared Layer
│   ├── ports/               # External interfaces
│   ├── adapters/            # Implementations
│   ├── infrastructure/      # Technical concerns
│   ├── kernel/              # DI container
│   └── domain/              # Shared entities
├── config/                  # Configuration
└── constants/               # Constants
```

**Key Principles:**
- **Inside (Application Core)**: Business logic in modules
- **Outside (Infrastructure)**: External services in adapters
- **Ports**: Interfaces defined by core, implemented by infrastructure
- **DI Container**: Service wiring and lifecycle management

## Request Flow Examples

### Chat Request Flow

```text
User Query
  ↓
POST /api/v1/chat/stream
  ↓
JWT Authentication
  ↓
Chat Module (chat.py)
  ↓
Classification Module
  - CompositeClassifier tries strategies
  - Returns ClassificationResult
  ↓
Handler Selection (via DI)
  - RAGHandler or ConversationalHandler
  ↓
Retrieval Module (if RAG)
  - Dense + BM25 → RRF → Rerank
  ↓
RAG Module (if RAG)
  - Context building → LLM generation
  ↓
SSE Streaming
  - routing → retrieval → thinking → content → citations
  ↓
Persistence
  - Save messages to PostgreSQL
```

### Document Upload Flow

```text
File Upload
  ↓
POST /api/v1/documents/upload
  ↓
MinIO Storage
  ↓
PostgreSQL Document Row
  ↓
Background Ingestion
  ↓
Extraction → Cleaning → Chunking → Embedding
  ↓
Qdrant Upsert (vectors)
  ↓
BM25 Index Update
  ↓
Status Update (complete)
```

## Configuration

### Environment Variables

```text
# Required
JWT_SECRET_KEY=<random-secret>
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
QDRANT_HOST=localhost
QDRANT_PORT=6333
MINIO_ENDPOINT=localhost:9000

# LLM Provider
LLM_PROVIDER=glm
GLM_API_KEY=<your-key>

# Embedding
EMBEDDING_BASE_URL=http://localhost:8001
EMBEDDING_MODEL=vietnamese-embedding
```

### Static Settings (settings.yaml)

```text
embedding:
  dim: 1024

retrieval:
  k: 5
  rrf_k: 60
  min_score_threshold: 0.65

reranking:
  enabled: true
  mode: "llm"
  top_k_before: 20
  top_k_after: 5

citations:
  max_citations: 10
  min_score_threshold: 0.3

chunking:
  size: 2048
  overlap: 256

semantic_routing:
  enabled: true
  threshold: 0.75

feature_flags:
  use_new_classification: false
  use_new_handlers: false
  enable_semantic_router: true

ragas_evaluation:
  enabled: false
```

## Development Setup

### Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd kira-simple

# 2. Start infrastructure
docker compose up -d

# 3. Backend setup
pip install -e ".[dev]"
python -m src.server.main

# 4. Frontend setup
cd frontend
npm install --legacy-peer-deps
npm run dev
```

### Access Points

- **Backend API**: http://localhost:8006
- **API Docs**: http://localhost:8006/docs
- **Frontend**: http://localhost:3001
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **MinIO Console**: http://localhost:9001

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Get current user

### Documents
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents` - List user documents
- `GET /api/v1/documents/{id}` - Get document detail
- `DELETE /api/v1/documents/{id}` - Delete document

### Chat
- `POST /api/v1/chat/stream` - Streaming chat
- `GET /api/v1/chat/conversations` - List conversations
- `GET /api/v1/chat/conversations/{id}` - Get conversation
- `DELETE /api/v1/chat/conversations/{id}` - Soft delete conversation

### Evaluation
- `POST /api/v1/evaluation/evaluate` - Single evaluation
- `POST /api/v1/evaluation/evaluate/batch` - Batch evaluation

### Metrics
- `GET /api/v1/metrics/routing/summary` - Routing metrics
- `GET /api/v1/metrics/routing/analysis` - Routing analysis

## Team & Process

- **Development**: Feature branch workflow
- **Code Review**: Required for all changes
- **Testing**: Pytest for backend, npm test for frontend
- **Linting**: Ruff (Python), ESLint (TypeScript)
- **Documentation**: Markdown in docs/ directory

## Roadmap

Current status: **Production-ready**

**Near-term Priorities:**
1. Complete test coverage (target: 70%+)
2. Performance optimization
3. CI/CD pipeline setup
4. Monitoring & alerting

**Long-term Goals:**
1. Advanced RAG techniques
2. Multi-modal support
3. Export/import conversations
4. Advanced search filters

## Liên kết nhanh

- [Kiến trúc Hệ thống](./system-architecture.md) - Architecture chi tiết với diagrams
- [Tiêu chuẩn Code](./code-standards.md) - Quy tắc đặt tên, tổ chức file, conventions
- [Hướng dẫn Thiết kế](./design-guidelines.md) - System design principles, patterns, UI/UX guidelines
- [Hướng dẫn Deployment](./deployment-guide.md) - Local setup, production deployment, monitoring
- [Lộ trình Phát triển](./project-roadmap.md) - Milestones, technical debt, changelog
- [CLAUDE.md](../CLAUDE.md) - Development guidelines chi tiết cho AI assistants

---

*Last Updated: 2026-06-12*
*Architecture: Hexagonal Modular Monolith*
*Status: Production-ready*
