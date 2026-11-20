# CLAUDE.md - KIRA Development Guide

Operating context for AI coding assistants and maintainers. `AGENTS.md` and `GEMINI.md` are symlinks to this file.

## Communication Policy

- Respond to user-facing questions in Vietnamese unless the user asks otherwise.
- Keep code, identifiers, comments, commit messages and technical documentation in English unless requested.
- Be concise, factual and implementation-oriented.

## Project Snapshot

KIRA is a full-stack RAG application: authenticated document upload, hybrid retrieval, citation-aware chat,
administrative drafting, a Vietnamese legal corpus with a knowledge graph, and RAG evaluation.

- Backend: FastAPI, Python 3.12, SQLAlchemy asyncio, Alembic (`backend/`)
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS (`frontend/`)
- Storage: PostgreSQL 16, Qdrant, MinIO, Neo4j (legal graph)
- Jobs: Celery + Redis
- Retrieval: dense (Qdrant) + BM25, RRF fusion, optional reranking (TEI or LLM)
- AI: OpenAI-compatible / GLM / Gemini / Ollama LLMs; TEI, Ollama or HTTP embedding API

## Repository Layout

```text
backend/                 Python service (pyproject.toml, uv.lock, alembic.ini, Dockerfile)
  kira/                  the application package
  tests/unit/<feature>/  unit tests, mirroring kira/<feature>/
  tests/integration/     tests that need Docker services (marker: integration)
  scripts/               one-off/maintenance scripts (not imported by kira)
frontend/                Next.js app (src/app routes, src/features, src/components, src/lib)
docs/                    architecture, deployment, evaluation docs; docs/archive for old plans
docker-compose.yml       infrastructure + app/tunnel profiles
Makefile                 all common commands (run `make help`)
```

## Backend Structure (feature-first)

```text
kira/
  main.py          FastAPI app: lifespan, CORS, error handlers, include_router - nothing else
  config.py        Settings (pydantic) + settings.yaml static defaults; REPO_ROOT
  deps.py          THE wiring file: provider singletons and service factories
  worker.py        Celery app (+ CeleryTaskQueue for revoking tasks)
  core/            technical helpers without business logic (logging, health, cors, errors, tracing)
  db/              session.py, models.py (all ORM), queries.py, migrate.py, migrations/ (Alembic)
  providers/       external services: llm/, embedding/, ocr.py, storage.py (MinIO), vector_store.py (Qdrant)
  auth/            login/register/JWT cookie/rate limit
  documents/       upload/list/delete/cancel + processing/ (extract, clean, chunk, embed pipeline) + tasks.py
  retrieval/       search.py (entry point), bm25.py, hybrid_search.py, fusion.py, rerank/
  chat/            router, sse.py (SSE contract), messages.py (persistence), service.py, graph.py,
                   intent/ (keyword -> cache -> LLM routing), handlers/ (conversational, rag, drafting),
                   rag/ (LangGraph pipeline: graph.py, state.py, nodes/, prompts/)
  drafting/        administrative document prompts and DOCX rendering
  legal/           legal corpus: router, services/, repository, parser, extraction/, temporal/, graph/ (Neo4j), tasks.py
  evaluation/      DeepEval service, datasets, metrics/, runners/, cli.py
  admin/           admin overview API
  pipeline_lab/    admin tool to inspect extraction/classification/reranking
```

Every feature uses the same file names where they apply:

| File | Holds |
|---|---|
| `router.py` | HTTP endpoints only: parse request, call a service, return a response |
| `service.py` or one file per operation (`upload.py`, `delete.py`, ...) | business logic |
| `repository.py` | all SQL for the feature |
| `schemas.py` | Pydantic/dataclass request and result models |
| `tasks.py` | Celery tasks |

## Architecture Rules

Enforced by `backend/tests/unit/test_architecture.py`:

1. Routers are leaves: only `kira/main.py` imports `*.router`.
2. No SQL in routers (`select(`, `db.execute(`, `from sqlalchemy import`); queries go in `repository.py`.
3. Only entry points (`router.py`, `sse.py`, `dependencies.py`, `tasks.py`, `cli.py`, `main.py`,
   `pipeline_lab/service.py`) read `kira.deps`. Services receive dependencies as constructor/function arguments.
4. Interfaces (ABC/Protocol) only where several real implementations exist:
   `providers/llm/base.py`, `providers/embedding/base.py`, `chat/intent/base.py`, `chat/handlers/base.py`,
   `legal/ports.py`, `legal/graph/base.py`. Otherwise use the concrete class; tests use fakes or monkeypatch.
5. `tests/unit/<x>/` must match a `kira/<x>/` folder.

Also:

- Features call each other through their public entry points (e.g. chat uses `retrieval.search`), not internals.
- Keep per-user isolation for documents, conversations, retrieval and citations (`user_id` on every query).
- No DI container, no new global mutable state. Add singletons in `deps.py` with `functools.cache`.
- Do not add an interface "for later". Add it when the second implementation arrives.
- Keep files under ~400 lines and functions under ~60 lines when you touch them (Boy Scout Rule: leave code
  cleaner than you found it, but do not mix large refactors into feature changes).

## Where To Change Things

| Change | Files |
|---|---|
| SSE event shape | `backend/kira/chat/sse.py` + `frontend/src/features/chat/streaming/` |
| RAG prompt / graph | `backend/kira/chat/rag/prompts/`, `chat/rag/graph.py`, `chat/rag/nodes/` |
| Intent routing | `backend/kira/chat/intent/` (chain built in `deps.get_classifier`) |
| New LLM/embedding provider | `backend/kira/providers/<kind>/<name>.py` + its factory |
| Chunking / extraction | `backend/kira/documents/processing/` |
| Hybrid search weights | `backend/kira/retrieval/` or `kira/settings.yaml` |
| New DB column | `backend/kira/db/models.py` + `make db-revision MSG="..."` |
| Wiring of anything | `backend/kira/deps.py` |

## Runtime Behavior

### Backend startup (`kira/main.py` lifespan)

1. `init_db()` runs Alembic migrations (`kira/db/migrate.py`). A pre-Alembic database is stamped at baseline `0001` first.
2. Initializes the reranking LLM client and reranking service.
3. Logs a dependency health table (PostgreSQL, Qdrant, Neo4j, MinIO, Redis, Celery, embedding, reranker, LLM, OCR, Docling).
   A DOWN service does not stop startup; it fails when used.

### Document upload

```text
POST /api/v1/documents/upload -> documents/router.py -> documents/upload.py
  -> MinIO (providers/storage.py) + documents row (documents/repository.py)
  -> Celery documents.process (documents/tasks.py) -> documents/process.py
  -> processing/pipeline.py: extract -> clean -> chunk -> embed -> Qdrant + BM25 -> status
```

Requires Redis and a running worker: `make dev-worker`.

### Chat streaming

```text
POST /api/v1/chat/stream -> chat/router.py -> chat/sse.py stream_chat_events
  -> chat/messages.py (load/create conversation, history)
  -> deps.get_chat_use_case() -> chat/graph.py: classify (chat/intent) -> dispatch handler
     conversational | rag (chat/rag LangGraph) | drafting | legal_qa (LEGAL_ENABLED=true)
  -> SSE events -> chat/messages.py saves user + assistant messages
```

The frontend parses SSE events in `frontend/src/features/chat/streaming/`. Change both sides together.

## Configuration Notes

- `.env` lives at the repo root; `kira/config.py` reads it from there (or from the working directory).
- `JWT_SECRET_KEY` is required. `APP_ENV=production` rejects known default secrets.
- Ports: backend `8006`, frontend dev `3001`, Docker frontend `3002`, PostgreSQL host port from `.env`.
- Qdrant vector size (default 1024) must match the embedding output.
- Legal features need the `neo4j` service, `NEO4J_*` settings and `LEGAL_ENABLED=true`.

## Commands

```bash
make help              # list everything
make infra             # docker compose up -d (infrastructure)
make install-backend   # cd backend && uv sync --extra dev
make dev-backend       # python -m kira.main (from backend/)
make dev-worker        # celery -A kira.worker.celery_app worker
make dev-frontend      # next dev on :3001
make db-migrate        # alembic upgrade head
make db-revision MSG="add column x"
make test-backend      # pytest -m "not integration"
make test-integration  # needs make infra
make test-frontend     # vitest
make lint              # ruff + eslint
make format            # ruff format + eslint --fix
make deploy / deploy-tunnel / deploy-stop
```

## Verification Before Committing

Backend (from `backend/`):

```bash
.venv/bin/ruff check kira tests
.venv/bin/ruff format --check kira tests
.venv/bin/mypy kira
.venv/bin/pytest -m "not integration"
```

Frontend (from `frontend/`):

```bash
npx eslint src/
npx tsc --noEmit -p .
npx vitest run --maxWorkers=4
```

Run the full suites when touching auth, DB models, document processing, retrieval, SSE shapes,
providers or the frontend API clients.

## Code Standards

- Python 3.12 syntax, absolute imports from `kira...`, type hints on public functions, async I/O kept async.
- Ruff rules: E, F, W, I, B, UP, N, SIM, RET, C4 (see `backend/pyproject.toml`). Line length 100.
- Do not swallow exceptions silently; log context and return safe API errors.
- Frontend: component files `PascalCase.tsx`, other modules `kebab-case.ts`, imports via `@/`.
  Feature code lives in `src/features/<feature>/` (components, hooks, stores, `api.ts`);
  shared UI in `src/components/{ui,layout,common}`; shared helpers in `src/lib/` (`lib/api/http.ts`).
- Docs: setup/product changes in `README.md`, assistant/developer guidance here, deep dives in `docs/`.

## Git

- Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`), imperative mood.
- Check `git status --short` before editing; never revert unrelated user changes.
- Never commit `.env`, credentials or tokens.
- No destructive commands (`git reset --hard`, broad deletes, `make db-reset`) unless explicitly requested.
- Do not add dependencies unless the existing stack cannot reasonably solve the task.
- If a command fails because infrastructure is down, name the missing service.
