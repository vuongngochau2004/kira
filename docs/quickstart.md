# KIRA quickstart

Run the backend and frontend locally, with PostgreSQL, Qdrant, MinIO, Redis, and Neo4j in Docker. Run all commands from the repository root unless a step says otherwise.

## Prerequisites

- Python 3.12+, Node.js 20+, npm, Docker with Compose v2, and `make`.
- Access to an LLM endpoint and an embedding service. The example values in `.env.example` are placeholders.
- Available local ports: `8006` (API), `3001` (web), `5433` (PostgreSQL), `6333` (Qdrant), `9000`/`9001` (MinIO), `6379` (Redis), and `7474`/`7687` (Neo4j).

## 1. Configure the environment

```bash
cp .env.example .env
```

Edit `.env` before starting the app:

- Set `JWT_SECRET_KEY` to a unique random value, for example one generated with `openssl rand -hex 32`.
- Configure the selected `LLM_PROVIDER` and its endpoint, model, and API key. For the default `openai_compatible` provider, set `BK_LLM_BASE_URL`, `BK_LLM_MODEL`, and `BK_API_KEY`.
- Configure `EMBEDDING_PROVIDER` and a reachable embedding endpoint. The template selects `aivn`, so replace `AIVN_EMBEDDING_BASE_URL` with your service URL. For TEI, set `EMBEDDING_PROVIDER=tei`, `TEI_BASE_URL`, and `TEI_API_KEY` if required by the service.
- Keep `POSTGRES_PORT=5433` unless you also need to change the local port mapping. The embedding vector dimension must match the selected model and Qdrant collection.

Keep `.env` private; it contains credentials.

## 2. Install dependencies

```bash
make install-backend   # cd backend && uv sync --extra dev -> backend/.venv
cd frontend
npm ci --legacy-peer-deps
cd ..
```

## 3. Start infrastructure

```bash
make infra
make infra-status
```

Wait until PostgreSQL and the other containers are running. The schema is created by Alembic when the backend starts (or with `make db-migrate`).

## 4. Start the app

Open three terminals at the repository root:

```bash
# Terminal 1: API
make dev-backend
```

```bash
# Terminal 2: document processing worker
make dev-worker
```

```bash
# Terminal 3: web app
make dev-frontend
```

Each `make dev-*` command activates `backend/.venv` or runs npm as needed. The backend applies Alembic migrations on startup. The worker is required for uploaded documents to progress beyond `pending`.

If `tmux` is installed, `make dev` starts these three processes in one session after infrastructure is running.

## 5. Open and verify

- Web app: <http://localhost:3001>
- API health: <http://localhost:8006/health>
- API documentation: <http://localhost:8006/docs>

Create an account in the web app, upload a document, wait for processing to complete, then open chat. A reachable embedding service is required for ingestion and retrieval. The backend logs a startup health report for its external dependencies.

## Stop and troubleshoot

Stop the three local processes with `Ctrl+C`. Stop infrastructure with `make infra-stop`; this keeps Docker volumes. Use `docker compose logs <service>` for a failing container, or `make infra-status` for container status.

The README mentions `make db-migrate`, but that Make target currently calls `python -m scripts.migrate`, and that module is absent. Do not rely on it for initial setup. If the API fails during database initialization, inspect the PostgreSQL logs and existing schema before changing any data.

For a containerized application build, see [Deployment Guide](docs/deployment-guide.md). `make deploy` uses the `app` Compose profile and exposes the web app at <http://localhost:3002> by default; external LLM and embedding services still need valid configuration.
