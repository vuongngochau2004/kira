# AGENTS.md - KIRA Development & Engineering Guide

This file provides comprehensive guidelines, architectural boundaries, coding standards, and operating context for AI coding assistants and developers working on the KIRA codebase.

---

## 1. Core Philosophy: The Boy Scout Rule (Anti-Drift)

> **"Older parts of the codebase may contain legacy debt. The agent MUST NOT copy existing anti-patterns. All new code and refactored functions must adhere strictly to the clean standards below. Always leave the codebase cleaner than you found it."**

- **Do not propagate bad patterns**: If an existing file lacks type hints, has untyped `any`, inline imports, or 400-line functions, do NOT follow that style.
- **Incremental refactoring**: Improve type hints, modularity, and error handling whenever modifying existing files without introducing breaking changes.

---

## 2. Communication Policy

- **Language for conversation**: Respond to user queries in **Vietnamese** unless explicitly requested otherwise.
- **Technical identifiers & code**: Keep all code, variable names, function names, class names, schema definitions, docstrings, inline comments, commit messages, and documentation in **English**.
- **Tone**: Concise, factual, implementation-focused, and proactive in identifying potential edge cases or bugs.

---

## 3. Project Overview & Tech Stack

KIRA is a production-grade full-stack RAG (Retrieval-Augmented Generation) application featuring authenticated document ingestion, hybrid search, citation-aware streaming chat, and comprehensive evaluation.

| Layer | Technologies & Runtimes |
|---|---|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0 (asyncio + asyncpg), Alembic, Pydantic v2 |
| **Frontend** | Node.js 20+, Next.js 16 (App Router), React 19, TypeScript 5, Tailwind CSS v4, Radix UI, Zustand, TanStack Query |
| **Storage & Vectors** | PostgreSQL 16 (+ pgvector), Qdrant (dense vector collection), MinIO (S3-compatible object storage) |
| **Background Processing**| Redis 7, Celery 5.4+ (document chunking, extraction, embedding) |
| **Search & Retrieval** | Dense vectors (1024-dim), BM25 keyword search, Reciprocal Rank Fusion (RRF), cross-encoder / LLM reranking |
| **AI / LLM Providers** | GLM / ZhipuAI (default), Google Gemini (`google-genai`), OpenAI-compatible API, LangGraph, DeepEval |
| **Architecture** | Hexagonal Architecture (Ports & Adapters) inside a Modular Monolith |

---

## 4. Architecture & Boundary Rules

### 4.1 Dependency Rule (Hexagonal Architecture)

Preserve strict dependency direction:

```text
src/server/ (FastAPI Routers & Middleware)
    └──> src/modules/<module>/api/ (Endpoints & Schemas)
            └──> src/modules/<module>/application/ (Use Cases & DTOs)
                    └──> src/modules/<module>/domain/ (Entities, Rules, Ports)
                            └──> src/modules/<module>/infrastructure/ (DB Repositories, Adapters)
                                    └──> src/shared/ (Shared Kernel, Ports & Common Adapters)
```

### 4.2 Module Boundaries & Responsibilities

- `src/modules/chat/`: Chat session management, message history, SSE streaming responses, citation binding.
- `src/modules/classification/`: Query intent classification (conversational, RAG, direct QA, drafting).
- `src/modules/document/`: Document upload, parsing/extraction, chunking, status tracking, MinIO integration.
- `src/modules/retrieval/`: Hybrid retrieval engine (Qdrant dense + BM25 keyword + RRF fusion + Reranking).
- `src/modules/rag/`: LangGraph RAG orchestration, multi-agent workflows, state management, prompt templates.
- `src/modules/evaluation/`: DeepEval test runners, evaluation datasets, metric generation.
- `src/shared/`: Shared kernel, common domain models, port interfaces, infrastructure clients (DB, MinIO, Redis).
- `src/server/`: FastAPI initialization, lifespan management, router mounting, CORS, global exception handlers.

### 4.3 Key Architectural Constraints

1. **No Business Logic in Endpoints**: FastAPI router functions must only handle HTTP validation, call application use cases, and return responses.
2. **Ports & Adapters Isolation**: Application and domain code must depend only on port interfaces (`src/shared/ports/` or module-internal ports), never directly on concrete adapter implementations.
3. **No Direct DB Queries in Use Cases**: Application services must access persistence exclusively through repository interfaces.
4. **Strict Multi-Tenancy**: Every document, chunk, conversation, message, and retrieval query MUST be filtered by `user_id`. Never leak context across users.
5. **Centralized Service Registration**: Wire dependencies in dependency injection containers or lifespan setup (`src/server/main.py`), not ad-hoc across modules.
6. **No Global Mutable State**: Use FastAPI dependencies (`Depends`) and service instances managed via lifespan.

---

## 5. Code Style & Language Guidelines

### 5.1 Python Standards (PEP 8 & Clean Code)

- **Python Version**: Python 3.12+.
- **Formatting**: Max line length **100 characters** (enforced by Ruff). Use 4 spaces for indentation.
- **Top-Level Imports Only**: All imports must be placed at the top level of the file. Group imports into 3 distinct blocks separated by a blank line:
  1. Standard library (`import os`, `from typing import ...`)
  2. Third-party packages (`from fastapi import ...`, `import torch`)
  3. Internal application packages (`from src.modules.chat...`, `from src.shared...`)
  - **No inline imports**: Never place `import` inside functions or methods.
  - **No import fallbacks**: Avoid `try...except ImportError` fallback patterns. Declare all required dependencies in `pyproject.toml`.
- **Type Annotations**:
  - Full type hints are **mandatory** on all function arguments and return types.
  - Use modern Python 3.12 union syntax: `str | None` instead of `Optional[str]`, `list[str]` instead of `List[str]`.
- **Categorical Options**: Always use Python `enum.StrEnum` for finite categorical choices (e.g., document status, message roles, intent types) instead of arbitrary string literals.
- **Docstrings (PEP 257)**: Use Google docstring style for public classes, methods, and functions.
- **Error Handling**:
  - Do not silently swallow exceptions (`except Exception: pass` is strictly forbidden).
  - Log errors with contextual data using `loguru.logger` and raise domain/HTTP exceptions appropriately.

### 5.2 TypeScript & Frontend Standards

- **TypeScript Version**: TypeScript 5+ with strict mode enabled.
- **Strict Typing Policy**:
  - **Zero `any` tolerance**: Never use `any`. Use `unknown` combined with type guards, or define explicit generic types / interfaces.
  - Exported functions, hooks, and React components must have explicit return types and typed props.
- **Schema Validation**: Use **Zod** (`zod`) as the single source of truth for API schemas, form schemas, and runtime validation.
- **Component Architecture**:
  - Distinguish clearly between Next.js Server Components and Client Components (`"use client"`).
  - Keep client components focused on interaction and UI state; delegate data mutations to hooks or API clients.
  - Reuse shared UI components in `frontend/src/components/ui/` (Radix UI / Tailwind primitives) instead of building custom raw inputs/buttons.
- **State Management**:
  - Local component state: `useState`, `useReducer`.
  - Global / Cross-component UI state: **Zustand** stores (`frontend/src/lib/stores/`).
  - Server state & caching: **TanStack React Query** (`@tanstack/react-query`).
- **Naming Conventions**:
  - Components & Types: `PascalCase` (e.g., `ChatPanel.tsx`, `ChatMessageProps`).
  - Hooks: `camelCase` with `use` prefix (e.g., `useStreamingChat.ts`).
  - Utilities & Helpers: `camelCase` (e.g., `formatTimestamp.ts`).
  - Directories: `kebab-case` or Next.js route conventions.

---

## 6. Pre-Commit Verification (Zero-Error Policy)

Before committing any changes, the agent or developer **MUST** run and pass the following verification checks without any errors or unhandled warnings:

### Backend Checks
```bash
# 1. Lint and style check
ruff check src/ tests/

# 2. Format check
ruff format --check src/ tests/

# 3. Static type check
mypy src/

# 4. Unit & regression tests
pytest tests/ -v
```

### Frontend Checks
```bash
# From the frontend/ directory:
cd frontend

# 1. ESLint check
npm run lint

# 2. TypeScript compilation check
npx tsc --noEmit

# 3. Component and unit tests
npm test
```

> **IMPORTANT**: Committing code with failed linting, broken type checks, or failing tests is strictly prohibited.

---

## 7. Git & Commit Workflow

### 7.1 Conventional Commits v1.0.0
All commit messages must follow the Conventional Commits specification:

```text
<type>(<scope>): <short imperative description>

[optional body]

[optional footer(s)]
```

- **Types**: `feat`, `fix`, `refactor`, `perf`, `test`, `chore`, `docs`, `style`.
- **Approved Scopes**:
  - `chat`: Chat APIs, streaming handlers, message persistence.
  - `retrieval`: Qdrant vector search, BM25, hybrid fusion, reranking.
  - `document`: Ingestion, extraction, chunking, MinIO storage.
  - `classification`: Query classification, intent routing.
  - `rag`: LangGraph agent workflows, prompt engineering.
  - `eval`: DeepEval evaluation pipelines and datasets.
  - `auth`: JWT authentication, permissions, user management.
  - `frontend` or `ui`: Next.js pages, React components, Tailwind styling, Zustand stores.
  - `infra`: Docker Compose, PostgreSQL, Qdrant, MinIO, Redis configurations.
  - `deps`: Dependency updates.

### 7.2 Safety & Secret Prevention
- **Never commit credentials**: Never stage `.env`, private keys, API tokens, passwords, or production secrets.
- **Never commit generated artifacts**: Ignore `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.next`, `dist`, `coverage`.

---

## 8. Runtime & Operational Procedures

### 8.1 Key Service Ports

- Backend API: `http://localhost:8006`
- Frontend Web: `http://localhost:3001`
- PostgreSQL: `localhost:5433` (Docker Compose mapping)
- Qdrant Vector DB: `localhost:6333`
- MinIO S3 API: `localhost:9000` (Console on `9001`)
- Redis: `localhost:6379`

### 8.2 Common Development Commands

```bash
# Start all infrastructure services
make infra

# Start backend server
make dev-backend
# Or: python -m src.server.main

# Start Celery worker for document processing
make dev-worker
# Or: celery -A src.worker.celery_app.celery_app worker --loglevel=info --concurrency=2

# Start frontend application
make dev-frontend
# Or: cd frontend && npm run dev

# Run comprehensive test suites
make test-backend
make test-frontend
```

### 8.3 Core Data Flows

1. **Document Ingestion**:
   `POST /api/v1/documents/upload` $\rightarrow$ Authenticate user $\rightarrow$ Store original file in MinIO $\rightarrow$ Insert DB record (`status=pending`) $\rightarrow$ Enqueue Celery task `documents.process` $\rightarrow$ Extract text/tables $\rightarrow$ Clean & chunk $\rightarrow$ Generate embeddings $\rightarrow$ Upsert to Qdrant $\rightarrow$ Build BM25 index $\rightarrow$ Update DB record (`status=completed`).

2. **SSE Streaming Chat**:
   `POST /api/v1/chat/stream` $\rightarrow$ Authenticate $\rightarrow$ Load conversation $\rightarrow$ Classify query intent $\rightarrow$ Retrieve relevant chunks (dense + sparse + rerank) $\rightarrow$ Stream SSE tokens/citations to frontend $\rightarrow$ Save user & assistant messages to PostgreSQL.

---

## 9. Common Pitfalls & Safety Rules

1. **Embedding Dimension Match**: Qdrant vector dimension is `1024` by default. It MUST match the external embedding model dimensions.
2. **Celery Worker Requirement**: File uploads will remain stuck in `pending` if Redis or the Celery worker is not running.
3. **Startup Health Check**: The backend lifespan verifies the Embedding API health on boot. If the embedding service is down, backend startup will fail.
4. **SSE Contract Integrity**: The frontend relies on exact SSE event structures (`token`, `citation`, `error`, `done`). Do not alter SSE message payloads without updating `frontend/src/lib/hooks/use-streaming-chat.ts`.
5. **No Destructive Operations**: Never run `git reset --hard`, `git checkout --`, or `make db-reset` without explicit user confirmation.
