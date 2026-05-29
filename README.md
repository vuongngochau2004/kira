# K.I.R.A Simplified

> Knowledge-based Intelligent Retrieval Assistant - RAG system with 4-layer architecture and hybrid retrieval

## Overview

K.I.R.A Simplified is a production-ready RAG (Retrieval-Augmented Generation) system following the **4-layer architecture pattern**. It combines dense vector search with BM25 keyword retrieval using Reciprocal Rank Fusion (RRF) for optimal document retrieval.

### Key Features

- **4-Layer Architecture**: Clean separation across Serving, Agent/Tools, Retrieval, and Ingestion layers
- **Hybrid Retrieval**: Combines dense (Qdrant) and BM25 with RRF fusion
- **LangChain Tools**: Tool-based design for agent integration
- **Vietnamese Optimized**: BAAI/bge-m3 embeddings, GLM LLM support
- **Multi-User**: Per-user BM25 indexes and document isolation
- **Streaming Responses**: Real-time SSE streaming for chat
- **Authentication**: JWT-based auth with user management

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SERVING LAYER                                     │
│  FastAPI (src/api/) - Auth, Documents, Chat endpoints                       │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT/TOOLS LAYER                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐                       │
│  │   src/agents/        │  │   src/tools/         │                       │
│  │   - rag_agent.py     │  │   - retrieval_tools  │  LangChain @tool      │
│  │   - llm.py           │  │   - ingestion_tools  │  decorators           │
│  │   - orchestrator.py  │  │                      │                       │
│  └──────────────────────┘  └──────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RETRIEVAL LAYER                                    │
│  src/retrieval/ - Dense (Vector), BM25 (Keyword), Hybrid (RRF)            │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INDEXING LAYER                                     │
│  src/indexing/ - Qdrant (Vector DB), Postgres (Metadata), MinIO (Files)   │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INGESTION LAYER                                    │
│  src/ingestion/ - Extract → Clean → Chunk → Embed → Index                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
kira-simple/
├── config/
│   ├── config.py           # Pydantic settings
│   └── prompts/            # Jinja2 prompt templates
│
├── src/
│   ├── api/                # SERVING LAYER
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── chat.py          # Chat completions (streaming)
│   │   └── documents.py     # Document CRUD
│   │
│   ├── agents/             # AGENT LAYER
│   │   ├── rag_agent.py     # Agentic RAG with self-evaluation
│   │   ├── llm.py           # LLM client wrapper
│   │   ├── prompts.py       # LLM prompts
│   │   └── utils.py         # Helper functions
│   │
│   ├── tools/              # TOOLS LAYER (NEW)
│   │   ├── retrieval_tools.py    # LangChain tools for retrieval
│   │   └── ingestion_tools.py    # LangChain tools for ingestion
│   │
│   ├── retrieval/          # RETRIEVAL LAYER
│   │   ├── dense.py         # Vector similarity search
│   │   ├── bm25.py          # BM25 keyword search
│   │   └── hybrid.py        # RRF hybrid search
│   │
│   ├── indexing/           # INDEXING LAYER (renamed from storage)
│   │   ├── qdrant_store.py  # Qdrant vector DB client
│   │   ├── document_store.py # PostgreSQL ORM
│   │   └── file_store.py    # MinIO file storage
│   │
│   ├── ingestion/          # INGESTION LAYER
│   │   ├── extractor.py     # File text extraction
│   │   ├── cleaner.py       # Text preprocessing
│   │   ├── chunker.py       # Document chunking
│   │   ├── embedding.py     # Embedding generation
│   │   ├── bm25_builder.py  # BM25 index management
│   │   └── pipelines.py     # End-to-end ETL
│   │
│   ├── auth/               # JWT authentication
│   ├── database/           # SQLAlchemy models + session
│   ├── models/             # Pydantic schemas
│   └── main.py             # FastAPI application entry
│
├── tests/                   # Integration tests
├── frontend/               # Next.js 16 UI
├── .env.example            # Environment variables template
├── docker-compose.yml      # Infrastructure (Postgres, Qdrant, MinIO)
└── pyproject.toml          # Python dependencies
```

## Installation

### Prerequisites

- Python >= 3.12
- Docker (for Qdrant, Postgres, MinIO)

### Setup

1. **Clone and navigate:**
```bash
cd kira-simple
```

2. **Install dependencies:**
```bash
pip install -e .
```

3. **Start infrastructure:**
```bash
docker compose up -d
```

4. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Run backend:**
```bash
python -m src.main
```

Backend runs on http://localhost:8006

### Optional: Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

Frontend runs on http://localhost:3000

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Get current user

### Documents
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents` - List documents
- `GET /api/v1/documents/{id}` - Get document details
- `DELETE /api/v1/documents/{id}` - Delete document
- `POST /api/v1/documents/{id}/process` - Trigger processing

### Chat
- `POST /api/v1/chat/completions` - Non-streaming chat
- `POST /api/v1/chat/stream` - Streaming chat (SSE)
- `GET /api/v1/chat/conversations` - List conversations
- `POST /api/v1/chat/conversations` - Create conversation
- `GET /api/v1/chat/conversations/{id}` - Get conversation with messages

### Health
- `GET /health` - Health check
- `GET /health/ready` - Readiness check
- `GET /health/live` - Liveness check

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | PostgreSQL host | localhost |
| `POSTGRES_PORT` | PostgreSQL port | 5433 |
| `QDRANT_HOST` | Qdrant host | localhost |
| `QDRANT_PORT` | Qdrant port | 6333 |
| `MINIO_ENDPOINT` | MinIO endpoint | localhost:9000 |
| `GLM_API_KEY` | Z.ai GLM API key | - |
| `EMBEDDING_MODEL` | Embedding model | BAAI/bge-m3 |
| `JWT_SECRET_KEY` | JWT secret | - |

## How It Works

### Retrieval Flow

```
1. User Query
   ↓
2. Query Embedding (BAAI/bge-m3)
   ↓
3. Strategy Selection (Dense/Hybrid)
   ↓
4. Parallel Retrieval:
   ├─ Dense Search (Qdrant vector similarity)
   └─ BM25 Search (Keyword matching)
   ↓
5. RRF Fusion (Reciprocal Rank Fusion)
   ↓
6. Context Building
   ↓
7. LLM Generation (GLM/Claude/GPT)
   ↓
8. Response with Citations
```

### Ingestion Pipeline

```
1. File Upload (MinIO)
   ↓
2. Text Extraction (PDF/DOCX/PPTX/TXT)
   ↓
3. Text Cleaning (Normalization)
   ↓
4. Document Chunking (Token-aware)
   ↓
5. Embedding Generation (BAAI/bge-m3)
   ↓
6. Storage:
   ├─ Qdrant (Vector embeddings)
   ├─ Postgres (Document metadata)
   └─ BM25 Index (In-memory keyword index)
```

## Technology Stack

- **API**: FastAPI with SSE streaming
- **Database**: PostgreSQL (SQLAlchemy async)
- **Vector DB**: Qdrant
- **File Storage**: MinIO
- **LLM**: Anthropic Claude, OpenAI, Zhipu GLM
- **Embeddings**: BAAI/bge-m3 (Vietnamese optimized)
- **Tools**: LangChain Core (@tool decorators)
- **Frontend**: Next.js 16

## Architecture Compliance

This project follows the 4-layer architecture pattern from `agentic-rag`:

| Layer | Module | Status |
|-------|--------|--------|
| **SERVING** | `src/api/` | ✅ |
| **AGENT/TOOLS** | `src/agents/` + `src/tools/` | ✅ |
| **RETRIEVAL** | `src/retrieval/` + `src/indexing/` | ✅ |
| **INGESTION** | `src/ingestion/` | ✅ |

## Testing

```bash
pytest tests/
```

## Differences from agentic-rag

| Feature | agentic-rag | kira-simple |
|---------|-------------|-------------|
| **Focus** | Vietnamese legal docs | General purpose RAG |
| **Auth** | None | JWT authentication |
| **Multi-user** | Single user | Per-user isolation |
| **Storage** | HuggingFace datasets | File upload (MinIO) |
| **BM25** | Global index | Per-user BM25 index |
| **UI** | Chainlit | Next.js (optional) |

## License

MIT
