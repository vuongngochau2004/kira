# K.I.R.A Simplified

Knowledge-based Intelligent Retrieval Assistant - a production-ready RAG application with hexagonal modular monolith architecture, hybrid retrieval, document ingestion, and evaluation tooling.

## What This Project Is

K.I.R.A Simplified lets users upload documents, index their content, and answer questions with retrieved context and citations. The backend is a Python modular monolith following hexagonal architecture principles. The frontend is a Next.js chat and document-management UI.

**Core Capabilities:**

- Authenticated multi-user document upload and chat
- PDF/DOCX/PPTX/TXT extraction pipeline with OCR support
- Dense vector retrieval through Qdrant
- Keyword retrieval through BM25
- Hybrid search with Reciprocal Rank Fusion (RRF)
- Optional LLM reranking and citation verification
- Streaming chat responses over Server-Sent Events
- Conversation persistence with soft delete
- RAGAS-based evaluation endpoints and golden datasets
- Routing metrics for query classification analysis
- Agentic RAG with LangGraph integration
- Thinking visualization (Claude-style)

## Architecture Overview

The system follows a **hexagonal modular monolith** architecture:

```text
Frontend (Next.js)
      ↓
FastAPI serving layer (src/server/)
      ↓
Application modules (src/modules/)
      ↓
Shared contracts (src/shared/ports/ & src/shared/kernel/)
      ↓
Adapters & infrastructure (src/shared/adapters/, PostgreSQL, Qdrant, MinIO, OCR, LLM APIs)
```

**Key Architectural Principles:**

- **Inside (Application Core)**: `src/modules/` - Business logic, use cases, domain services
- **Outside (Infrastructure)**: `src/shared/adapters/`, `src/shared/infrastructure/` - External services, technical concerns
- **Ports**: `src/shared/ports/` - Interfaces defined by core, implemented by infrastructure
- **DI Container**: `src/shared/kernel/di/` - Service wiring and lifecycle management

**Module Structure:**

```text
src/modules/<context>/
├── api/              # Request/Response DTOs
├── application/      # Use cases and orchestration
├── domain/           # Business logic, strategies, services
└── infrastructure/   # Module-specific persistence/integration
```

**Current Modules:**
- **chat**: Chat use cases, handlers, streaming
- **classification**: Query routing strategies (Keyword → Cached → LLM)
- **document**: Document upload and ingestion pipeline
- **retrieval**: Dense, BM25, hybrid search with RRF
- **rag**: Agentic RAG with LangGraph
- **evaluation**: RAGAS evaluation services

See [docs/system-architecture.md](docs/system-architecture.md) for detailed architecture documentation.

## Repository Layout

```text
kira-simple/
├── src/
│   ├── server/                  # FastAPI app, routers, middleware
│   │   ├── main.py              # Main backend entrypoint
│   │   └── api/v1/              # Auth, chat, documents, evaluation, metrics APIs
│   ├── modules/                 # Modular monolith application contexts
│   │   ├── chat/                # Chat use cases, handlers, prompts, streaming
│   │   ├── classification/      # Query routing strategies and cache
│   │   ├── document/            # Upload and ingestion pipeline
│   │   ├── evaluation/          # RAGAS evaluation services and datasets
│   │   ├── rag/                 # Agentic RAG, LangGraph flow, prompts, state
│   │   └── retrieval/           # Dense, BM25, hybrid search, repositories
│   ├── shared/                  # Shared ports, adapters, infra, kernel, domain
│   │   ├── ports/               # LLM, vector store, embedding, OCR, storage contracts
│   │   ├── adapters/            # GLM, Qdrant, MinIO, PaddleOCR, embedding adapters
│   │   ├── infrastructure/      # Auth, DB, monitoring, logging, LLM clients
│   │   ├── kernel/              # DI container, registry, base interfaces
│   │   └── domain/              # Shared entities and value objects
│   ├── config/                  # Pydantic settings and static YAML config
│   ├── constants/               # Shared constants
│   └── tools/                   # Retrieval, ingestion, reranking tools
├── frontend/                    # Next.js 16 / React 19 frontend
├── tests/                       # Unit, integration, retrieval, evaluation tests
├── docs/                        # Architecture, roadmap, deployment docs
├── migrations/                  # Database initialization SQL
├── docker-compose.yml           # PostgreSQL + Qdrant + MinIO
├── Makefile                     # Common local commands
├── CLAUDE.md                    # AI assistant development guide
└── pyproject.toml               # Python package and tooling config
```

**Important**: The backend entrypoint is `src/server/main.py`. Use `src.server.main` for imports and ASGI references.

## Quick Start

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Node.js 20+ (for frontend development)
- A valid `JWT_SECRET_KEY`
- LLM/embedding services configured

### 1. Clone and Setup

```bash
git clone <repository-url>
cd kira-simple
```

### 2. Start Infrastructure

```bash
docker compose up -d
```

This starts:
- PostgreSQL 16 + pgvector (port 5433)
- Qdrant (ports 6333 HTTP, 6334 gRPC)
- MinIO (ports 9000 API, 9001 console)

### 3. Backend Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Create .env file
cat > .env << EOF
JWT_SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USER=kira
POSTGRES_PASSWORD=kira_secret
POSTGRES_DB=kira_dev
QDRANT_HOST=localhost
QDRANT_PORT=6333
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=kira_minio
MINIO_SECRET_KEY=kira_minio_secret
LLM_PROVIDER=glm
GLM_API_KEY=your-glm-api-key
EMBEDDING_BASE_URL=http://localhost:8001
EOF

# Run backend
python -m src.server.main
```

Backend runs on http://localhost:8006

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install --legacy-peer-deps

# Run dev server
npm run dev
```

Frontend runs on http://localhost:3001

### 5. Verify Setup

Check health endpoints:
```bash
curl http://localhost:8006/health
curl http://localhost:8006/health/ready
curl http://localhost:8006/health/live
```

Access API docs: http://localhost:8006/docs

## Common Commands

### Using Makefile

```bash
make help              # Show available commands
make infra             # Start infrastructure
make dev-backend       # Run backend (assumes .venv exists)
make dev-frontend      # Run frontend
make test-backend      # Run backend tests
make test-frontend     # Run frontend tests
make lint              # Run backend and frontend lint
make format            # Format backend and frontend
```

### Direct Commands

**Backend:**
```bash
# Install
pip install -e ".[dev]"

# Run
python -m src.server.main

# Test
pytest tests/ -v

# Lint/Format
ruff check src/ tests/
ruff format src/ tests/
```

**Frontend:**
```bash
cd frontend

# Install
npm install --legacy-peer-deps

# Run
npm run dev

# Lint
npm run lint

# Build
npm run build

# Test
npm test
```

**Infrastructure:**
```bash
docker compose up -d      # Start
docker compose ps         # Status
docker compose logs -f    # Logs
docker compose down       # Stop
```

## API Summary

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
- `POST /api/v1/chat/stream` - Streaming chat (SSE)
- `GET /api/v1/chat/conversations` - List conversations
- `GET /api/v1/chat/conversations/{id}` - Get conversation
- `DELETE /api/v1/chat/conversations/{id}` - Soft delete conversation

### Evaluation
- `POST /api/v1/evaluation/evaluate` - Single evaluation
- `POST /api/v1/evaluation/evaluate/batch` - Batch evaluation

### Metrics
- `GET /api/v1/metrics/routing/summary` - Routing metrics
- `GET /api/v1/metrics/routing/analysis` - Routing analysis

## Configuration

### Environment Variables

**Required:**
- `JWT_SECRET_KEY` - JWT signing secret
- `POSTGRES_*` - Database connection
- `QDRANT_*` - Vector store connection
- `MINIO_*` - Object storage connection

**LLM Provider:**
- `LLM_PROVIDER` - glm, gemini, or openai
- `GLM_API_KEY`, `GEMINI_API_KEY`, or `OPENAI_API_KEY`

**Embedding:**
- `EMBEDDING_BASE_URL` - Embedding service URL
- `EMBEDDING_MODEL` - Model name
- `EMBEDDING_DIM` - Vector dimension (default: 1024)

### Static Configuration (src/config/settings.yaml)

Controls:
- Retrieval parameters (top-k, RRF constant, score threshold)
- Reranking settings (mode, limits)
- Citation behavior (limits, verification, snippet length)
- Chunking parameters (size, overlap)
- Qdrant settings (collection, vector dimension)
- Semantic routing (threshold)
- Feature flags (classification, handlers, semantic router)
- RAGAS evaluation (enabled flag, metrics, timeout)

## Documentation

- **[System Architecture](docs/system-architecture.md)** - Detailed architecture with diagrams
- **[Project Overview](docs/project-overview.md)** - Tech stack, capabilities, configuration
- **[Project Roadmap](docs/project-roadmap.md)** - Milestones, technical debt, priorities
- **[Code Standards](docs/code-standards.md)** - Naming conventions, file organization, patterns
- **[Design Guidelines](docs/design-guidelines.md)** - Design principles, API patterns, UI/UX
- **[Deployment Guide](docs/deployment-guide.md)** - Local setup, production deployment, monitoring
- **[CLAUDE.md](CLAUDE.md)** - Development guide for AI assistants

## Tech Stack

**Backend:**
- Python 3.12, FastAPI
- Hexagonal modular monolith architecture
- GLM-4.5 (primary LLM), Claude, GPT (backup)
- LangGraph for agentic RAG

**Frontend:**
- Next.js 16 (App Router), React 19
- TypeScript, Tailwind CSS, shadcn/ui
- Zustand (state), TanStack Query (data fetching)

**Database:**
- PostgreSQL 16 + pgvector
- Qdrant (vector DB)
- MinIO (object storage)

**Development:**
- Pytest, Ruff, MyPy
- Docker Compose
- ESLint, Prettier

## Current Status

**Phase:** Production-ready with Hexagonal Architecture ✅

**Completed:**
- ✅ Hexagonal modular monolith structure (6 modules)
- ✅ Shared layer (ports, adapters, infrastructure, kernel, domain)
- ✅ Hybrid retrieval (Dense + BM25 with RRF)
- ✅ Per-user data isolation
- ✅ Query classification (Strategy pattern)
- ✅ Agentic RAG with LangGraph
- ✅ SSE streaming responses
- ✅ JWT authentication with httpOnly cookies
- ✅ Frontend (Next.js 16 + React 19)

**Next Priorities:**
- 🔴 Testing & Quality (target: 70%+ coverage)
- 🟡 Performance optimization
- 🟢 Production deployment setup

## Contributing

See [docs/code-standards.md](docs/code-standards.md) for coding conventions and [CLAUDE.md](CLAUDE.md) for development guidelines.

**Quick Start:**
1. Follow hexagonal architecture principles
2. Respect module boundaries
3. Use ports/adapters for external services
4. Wire services through DI container
5. Keep HTTP concerns in `src/server/`
6. Add tests for new features

## License

[Specify your license here]

---

*Last Updated: 2026-06-12*
*Architecture: Hexagonal Modular Monolith*
*Python: 3.12 | Next.js: 16 | React: 19*
