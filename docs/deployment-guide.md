# Deployment Guide

This guide documents the current deployable shape of KIRA.

## Current Deployment Shape

The repository currently provides Docker Compose for infrastructure services only:

- PostgreSQL 16 + pgvector
- Qdrant
- MinIO
- Redis

The backend, Celery worker, and frontend are run from source during local development. Production container images can be added later, but they are not part of the current `docker-compose.yml`.

## Local Development

### Requirements

- Python 3.12+
- Node.js 20+
- Docker 24+
- Docker Compose 2+
- LLM provider credentials or a compatible endpoint
- Embedding API compatible with the configured embedding settings

### Start Infrastructure

```bash
docker compose up -d
docker compose ps
```

Default local ports:

| Service | URL/Port |
| --- | --- |
| PostgreSQL | `localhost:5433` |
| Qdrant HTTP | `http://localhost:6333` |
| Qdrant gRPC | `localhost:6334` |
| MinIO API | `http://localhost:9000` |
| MinIO Console | `http://localhost:9001` |
| Redis | `localhost:6379` |

### Environment File

Create `.env` at the repository root:

```bash
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
MINIO_BUCKET=kira-documents
MINIO_SECURE=false

REDIS_HOST=localhost
REDIS_PORT=6379
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

LLM_PROVIDER=glm
GLM_API_KEY=your-glm-api-key
GLM_MODEL=glm-4.5

EMBEDDING_BASE_URL=http://localhost:8001
EMBEDDING_MODEL=vietnamese-embedding-v2
EMBEDDING_DIM=1024

APP_ENV=development
DEBUG=true
AUTH_ENABLED=true
CORS_ORIGINS=http://localhost:3001,http://localhost:3000,http://localhost:8006
```

### Install Backend

```bash
pip install -e ".[dev]"
```

Optional extras:

```bash
pip install -e ".[dev,docling]"
pip install -e ".[dev,ml]"
```

### Run Backend

```bash
python -m src.server.main
```

Backend:

- API: http://localhost:8006
- Docs: http://localhost:8006/docs
- Health: http://localhost:8006/health

Backend startup checks the embedding API, so make sure `EMBEDDING_BASE_URL` is reachable.

### Run Worker

Document uploads enqueue Celery jobs. Keep the worker running when testing upload/ingestion:

```bash
celery -A src.worker.celery_app.celery_app worker --loglevel=info --concurrency=2
```

### Run Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

Frontend: http://localhost:3001

## Operational Checks

```bash
curl http://localhost:8006/health
curl http://localhost:8006/health/ready
curl http://localhost:8006/health/live
docker compose ps
docker compose logs -f redis
docker compose logs -f qdrant
```

Useful application checks:

1. Register or login through the frontend.
2. Upload a small PDF/DOCX/TXT document.
3. Confirm the worker receives a `documents.process` task.
4. Wait for document status to complete.
5. Ask a document-grounded question and verify citations are returned.

## Data Persistence

Docker volumes are defined in `docker-compose.yml`:

- `postgres_data`
- `qdrant_data`
- `minio_data`
- `redis_data`

Stopping services with `docker compose down` keeps data. Removing volumes deletes local data:

```bash
docker compose down -v
```

Use destructive reset commands only when local data can be discarded.

## Production Notes

Before production deployment, add or verify:

- Container images for backend, worker, and frontend
- A production compose, Kubernetes, or process-manager configuration
- HTTPS termination and secure cookie settings
- Strong `JWT_SECRET_KEY` and database/object-storage credentials
- Restricted `CORS_ORIGINS`
- Managed PostgreSQL/Qdrant/Redis/MinIO or hardened self-hosted equivalents
- Backup and restore procedures for PostgreSQL, Qdrant, and MinIO
- Monitoring for API latency, worker failures, queue depth, retrieval quality, and LLM errors
- Log aggregation and request tracing
- Migration strategy beyond one-time SQL initialization scripts

Production environment baseline:

```bash
APP_ENV=production
DEBUG=false
JWT_SECRET_KEY=<strong-random-secret>
CORS_ORIGINS=https://your-domain.example
POSTGRES_PASSWORD=<strong-password>
MINIO_SECRET_KEY=<strong-secret>
```

`APP_ENV=production` rejects known default JWT secrets at startup.

## Troubleshooting

| Symptom | Likely cause | Check |
| --- | --- | --- |
| Backend fails during startup | Embedding API unavailable or missing env | `EMBEDDING_BASE_URL`, backend logs |
| Upload returns enqueue error | Redis unavailable | `docker compose ps redis`, `CELERY_BROKER_URL` |
| Document remains processing | Worker not running or task failed | Celery worker logs |
| No retrieval results | Qdrant collection/index mismatch or no chunks | Qdrant dashboard/logs, document chunks endpoint |
| Auth works in API but not browser | Cookie/CORS mismatch | `CORS_ORIGINS`, frontend URL, browser devtools |
| Frontend cannot reach API | Wrong API base or backend port | backend `8006`, frontend client config |
