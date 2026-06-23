# AGENTS.md - KIRA Development Guide

This file gives AI coding assistants and maintainers the operating context for the KIRA repository.

## Communication Policy

- Respond to user-facing questions in Vietnamese unless the user asks otherwise.
- Keep code, identifiers, inline comments, commit text, and technical documentation in English unless specifically requested.
- Be concise, factual, and implementation-oriented.

## Project Snapshot

KIRA is a full-stack RAG application for authenticated document upload, hybrid retrieval, citation-aware chat, and RAG evaluation.

- Backend: FastAPI, Python 3.12, SQLAlchemy asyncio
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS
- Storage: PostgreSQL 16 + pgvector, Qdrant, MinIO
- Jobs: Celery + Redis for document processing
- Retrieval: dense vector search, BM25 keyword search, RRF hybrid fusion, optional reranking
- AI: GLM/Z.ai default, Gemini/OpenAI-compatible/Ollama options, external embedding API
- Architecture: hexagonal modular monolith

## Current Entry Points

### Backend

- FastAPI app: `src/server/main.py`
- Runtime settings: `src/config/config.py`
- Static settings: `src/config/settings.yaml`
- Database session: `src/shared/infrastructure/persistence/database/session.py`
- Database models: `src/shared/infrastructure/persistence/database/models.py`
- Celery app: `src/worker/celery_app.py`
- Document task: `src/worker/document_tasks.py`

### API Routers

- Auth: `src/server/api/v1/auth/endpoints.py`
- Chat: `src/modules/chat/api/endpoints.py`
- Documents: `src/modules/document/api/endpoints.py`
- Evaluation: `src/server/api/v1/evaluation/endpoints.py`
- Metrics: `src/server/api/v1/metrics/endpoints.py`

All routers are mounted in `src/server/main.py` under `/api/v1/...`.

### Frontend

- App routes: `frontend/src/app/`
- Main auth landing page: `frontend/src/app/page.tsx`
- Conversation page: `frontend/src/app/conversation/page.tsx`
- Upload page: `frontend/src/app/uploads/page.tsx`
- API client: `frontend/src/lib/api/simple-client.ts`
- Chat hooks: `frontend/src/lib/hooks/use-simple-chat.ts`, `use-streaming-chat.ts`
- Stores: `frontend/src/lib/stores/`
- Shared UI components: `frontend/src/components/ui/`

## Architecture Rules

The backend uses a hexagonal modular monolith. Preserve the dependency direction:

```text
src/server/ and module api/
        -> application use cases
        -> domain services and rules
        -> shared ports/contracts
        -> adapters/infrastructure
```

### Layer Responsibilities

- `src/server/`: FastAPI app setup, cross-cutting HTTP concerns, top-level router mounting
- `src/modules/<module>/api/`: module-owned request/response schemas and endpoint functions
- `src/modules/<module>/application/`: use cases, orchestration, application DTOs
- `src/modules/<module>/domain/`: business rules, prompts, strategies, domain services
- `src/modules/<module>/infrastructure/`: module-specific persistence or integrations
- `src/shared/ports/`: contracts for external services
- `src/shared/adapters/`: concrete implementations of ports
- `src/shared/infrastructure/`: DB, auth, monitoring, LLM clients, technical concerns
- `src/shared/kernel/`: dependency injection, base abstractions, registries

### Rules To Enforce

- Do not put business logic in FastAPI endpoint functions.
- Do not import concrete adapters into application/domain code when a port exists.
- Do not query SQLAlchemy directly from application/domain code; use repositories or owned infrastructure boundaries.
- Keep per-user isolation intact for documents, conversations, retrieval, and citations.
- Register/wire concrete services centrally instead of constructing them throughout the codebase.
- Avoid new global mutable state unless it matches an existing service singleton pattern.

## Module Map

- `chat`: chat use cases, handler selection, SSE streaming, conversation/message persistence
- `classification`: query intent routing, keyword/cache/LLM strategies
- `document`: upload, delete, download, chunk listing, background processing
- `retrieval`: Qdrant dense retrieval, BM25, hybrid search, reranking service
- `rag`: agentic/LangGraph RAG orchestration, state, agents, prompts
- `evaluation`: DeepEval evaluation service, golden datasets, CLI runner

## Runtime Behavior

### Backend Startup

`src/server/main.py` lifespan currently:

1. Initializes database connections.
2. Checks the embedding API through `EmbeddingAPIAdapter().health_check()`.
3. Initializes retrieval and ingestion tools.
4. Creates an LLM client for reranking/hybrid search support.
5. Initializes the reranking service and hybrid-search LLM client.
6. Closes DB connections on shutdown.

If backend startup fails early, check database availability, embedding API availability, and required environment variables.

### Document Upload Flow

```text
POST /api/v1/documents/upload
  -> authenticate user
  -> store original file in MinIO
  -> create PostgreSQL document row
  -> enqueue Celery task documents.process
  -> worker extracts/cleans/chunks/embeds
  -> upsert chunks into Qdrant
  -> update BM25/index metadata and document status
```

Local upload processing requires Redis and a running Celery worker:

```bash
celery -A src.worker.celery_app.celery_app worker --loglevel=info --concurrency=2
```

### Chat Streaming Flow

```text
POST /api/v1/chat/stream
  -> authenticate user
  -> load/create conversation
  -> classify query intent
  -> select conversational/RAG/drafting handler
  -> retrieve context when needed
  -> stream SSE events
  -> persist user and assistant messages
```

The frontend expects structured SSE event shapes. Be careful when changing event types or payload fields.

## Configuration Notes

- `JWT_SECRET_KEY` is required by Pydantic settings.
- `APP_ENV=production` rejects known default JWT secrets.
- Backend dev port is `8006`.
- Frontend dev port is `3001`.
- Docker Compose exposes PostgreSQL on host port `5433`.
- Qdrant vector dimension is `1024` by default and must match the embedding API output.
- Static retrieval/reranking/citation/chunking defaults live in `src/config/settings.yaml`.
- `.env` values override Pydantic runtime settings in `src/config/config.py`.

## Development Commands

### Infrastructure

```bash
docker compose up -d
docker compose ps
docker compose logs -f
docker compose down
```

### Backend

```bash
pip install -e ".[dev]"
python -m src.server.main
pytest tests/ -v
ruff check src/ tests/
ruff format src/ tests/
mypy src/
```

### Worker

```bash
celery -A src.worker.celery_app.celery_app worker --loglevel=info --concurrency=2
```

### Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
npm run lint
npm run build
npm test
```

### Makefile

```bash
make help
make infra
make dev-backend
make dev-worker
make dev-frontend
make test-backend
make test-frontend
make lint
make format
```

`make dev`, `make dev-backend`, and `make dev-worker` assume `.venv/bin/activate` exists.

## Testing Guidance

Use focused tests for narrow behavior and broader checks for shared contracts.

- Document pipeline: `tests/test_document_clean_chunk.py`, `tests/test_document_extractor_quality.py`
- Retrieval/reranking: `tests/test_retrieval_agent_reranking.py`
- Database checks: `test_db.py`
- Qdrant checks: `test_qdrant.py`
- Evaluation scripts: `scripts/validate_eval_dataset.py`, `scripts/evaluate_extraction_quality.py`

Run broader tests when touching:

- authentication
- database models/session behavior
- document processing
- retrieval contracts
- SSE streaming shapes
- shared ports/adapters
- frontend API client contracts

## Code Standards

### Python

- Use Python 3.12 syntax.
- Follow Ruff settings in `pyproject.toml`.
- Use absolute imports from `src...`.
- Add type hints for public functions and methods.
- Keep async behavior consistent for DB, HTTP, and streaming paths.
- Keep line length near 100 characters where practical.
- Do not silently swallow exceptions; log useful context and preserve safe API errors.

### Frontend

- Keep TypeScript typed at component, hook, and API boundaries.
- Reuse `frontend/src/components/ui/` and existing stores/hooks before adding new patterns.
- Keep app screens operational and direct; this is not a marketing site.
- Keep user-facing text consistent with the current Vietnamese/English locale structure.
- Preserve current SSE streaming compatibility unless updating frontend and backend together.

### Documentation

- Update `README.md` for setup, architecture, API, or product-facing workflow changes.
- Update `AGENTS.md` for assistant/developer guidance, entry points, boundaries, or command changes.
- Use `docs/` for deeper technical documentation.
- Put README screenshots in `docs/assets/` and reference stable relative paths.

## Safety Notes For AI Agents

- Check `git status --short` before editing.
- Do not revert unrelated user changes.
- Use `rg` or `rg --files` for search.
- Use `apply_patch` for manual file edits.
- Do not run destructive commands such as `git reset --hard`, `git checkout --`, or broad deletes unless explicitly requested.
- Be careful with `make db-reset`; it deletes local database volumes after confirmation.
- Do not add dependencies unless the existing stack cannot reasonably solve the task.
- If a command fails because infrastructure is unavailable, state the missing service instead of hiding the requirement.

## Common Pitfalls

- Use `src/server/main.py` as the ASGI/FastAPI entry point.
- Chat and document endpoints live under module API folders, not only under `src/server/api/v1/`.
- Frontend uses port `3001`, while CORS may still include `3000` for compatibility.
- Upload succeeds only when Redis and Celery can enqueue/process the task.
- Embedding API health is checked during backend startup.
- Qdrant collection/vector dimension must match configured embeddings.
- Keep retrieval and document queries scoped by `user_id`.
- Evaluation uses DeepEval naming in current code and docs; do not introduce a separate RAGAS-only path without checking implementation.
