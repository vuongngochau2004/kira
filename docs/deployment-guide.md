# Hướng dẫn Deployment

## Tổng quan

Document này hướng dẫn deployment K.I.R.A Simplified cho:
- Local development
- Staging environment
- Production environment

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 8 GB
- Disk: 20 GB

**Recommended:**
- CPU: 8+ cores
- RAM: 16+ GB
- Disk: 50+ GB SSD

### Software Requirements

- Docker 24.0+
- Docker Compose 2.20+
- Python 3.12+ (for local development)
- Node.js 20+ (for frontend development)
- PostgreSQL 16+ client (psql)

## Local Development Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd kira-simple
```

### 2. Environment Configuration

Tạo file `.env` từ template:

```bash
cp .env.example .env
```

Cấu hình các biến môi trường:

```bash
# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=kira
POSTGRES_PASSWORD=kira_secret
POSTGRES_DB=kira_dev

# JWT
JWT_SECRET_KEY=change-this-in-production-use-openssl-rand-hex-32
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# LLM Provider
LLM_PROVIDER=glm
GLM_API_KEY=your-glm-api-key

# Embedding
EMBEDDING_BASE_URL=http://your-embedding-api:8888
EMBEDDING_MODEL=vietnamese-embedding-v2

# OCR (optional)
OCR_ENABLED=true
OCR_BASE_URL=http://paddleocr-service:8868

# Application
APP_ENV=development
DEBUG=true
AUTH_ENABLED=true

# CORS
CORS_ORIGINS=http://localhost:3001,http://localhost:3000
```

### 3. Docker Compose Development

Khởi động tất cả services:

```bash
docker-compose up -d
```

Kiểm tra status:

```bash
docker-compose ps
```

Xem logs:

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f qdrant
```

### 4. Database Migration

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Create initial data
docker-compose exec backend python -m src.database.init_data
```

### 5. Access Services

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:3001
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **PostgreSQL**: localhost:5432
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

## Production Deployment

### 1. Production Environment Variables

```bash
# .env.production
APP_ENV=production
DEBUG=false

# Strong secrets
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
POSTGRES_PASSWORD=<strong-password>

# CORS (restrict to specific domains)
CORS_ORIGINS=https://your-domain.com

# Production database (consider managed service)
POSTGRES_HOST=your-production-db-host
POSTGRES_PORT=5432

# External services (use production endpoints)
LLM_API_KEY=production-api-key
EMBEDDING_BASE_URL=https://production-embedding-api

# Monitoring
SENTRY_DSN=<your-sentry-dsn>
LOG_LEVEL=INFO
```

### 2. Generate Secrets

```bash
# JWT Secret
openssl rand -hex 32

# Database Password
openssl rand -base64 32

# MinIO Secret Keys
openssl rand -base64 32
```

### 3. Docker Compose Production

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d
```

**Production Compose Differences:**
- No volume mounts for code (read-only images)
- External PostgreSQL/Qdrant (managed services)
- Redis for caching
- Health checks enabled
- Resource limits configured
- Auto-restart policies

### 4. Build Production Images

```bash
# Backend
docker build -t kira-backend:latest -f docker/backend/Dockerfile .

# Frontend
docker build -t kira-frontend:latest -f docker/frontend/Dockerfile frontend/
```

### 5. Database Setup

**Using Managed PostgreSQL (Recommended):**

```bash
# Run migrations
docker-compose --env-file .env.production run --rm backend \
    alembic upgrade head

# Create indexes
docker-compose --env-file .env.production run --rm backend \
    python -m src.scripts.create_indexes
```

## Infrastructure Options

### Option 1: Single Server (Docker Compose)

**Architecture:**
```
┌─────────────────────────────────────┐
│          Single Server              │
│  ┌───────────────────────────────┐ │
│  │  Docker Compose               │ │
│  │  ├── Backend (FastAPI)        │ │
│  │  ├── Frontend (Next.js)       │ │
│  │  ├── PostgreSQL + pgvector    │ │
│  │  ├── Qdrant                   │ │
│  │  ├── MinIO                    │ │
│  │  └── Nginx (reverse proxy)    │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Requirements:**
- 8+ CPU cores
- 16+ GB RAM
- 100+ GB SSD

**Pros:**
- Simple setup
- Cost-effective
- Easy management

**Cons:**
- Single point of failure
- Limited scalability
- Manual backup required

### Option 2: Cloud-Native (Kubernetes)

**Architecture:**
```
┌────────────────────────────────────────────┐
│         Kubernetes Cluster                 │
│  ┌──────────────────────────────────────┐ │
│  │  Namespace: kira                      │ │
│  │  ├── Deployment: backend              │ │
│  │  ├── Deployment: frontend             │ │
│  │  ├── StatefulSet: qdrant              │ │
│  │  ├── Ingress: nginx                   │ │
│  │  └── Services...                       │ │
│  └──────────────────────────────────────┘ │
└────────────────────────────────────────────┘
         │                    │
    ┌────┘                    └────┐
    │                              │
┌─────────┐                 ┌──────────┐
│ RDS/PG  │                 │ Qdrant   │
│ Cloud   │                 │ Cloud    │
└─────────┘                 └──────────┘
```

**Pros:**
- High availability
- Auto-scaling
- Self-healing
- Rolling updates

**Cons:**
- Complex setup
- Higher cost
- Requires K8s expertise

### Option 3: Hybrid (Recommended for Production)

**Architecture:**
```
┌──────────────────────────────────────────────┐
│         Application Server                    │
│  ├── Docker Compose                          │
│  │   ├── Backend (FastAPI)                    │
│  │   ├── Frontend (Next.js)                  │
│  │   └── Nginx                               │
│  └────────────────────────────────────────┐ │
└────────────────────────────────────────────┘
                                               │
                    ┌──────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
┌─────────┐    ┌─────────┐    ┌─────────┐
│ RDS/PG  │    │ Qdrant  │    │ MinIO   │
│ Cloud   │    │ Cloud   │    │ Cloud   │
└─────────┘    └─────────┘    └─────────┘
```

**Pros:**
- Managed databases (backups, HA)
- Simple application deployment
- Cost-effective
- Best of both worlds

## Monitoring & Logging

### 1. Application Logs

**Backend Logging (Python):**
```python
import logging

logger = logging.getLogger(__name__)

# Different log levels
logger.debug("Detailed debug info")
logger.info("User action completed")
logger.warning("High latency detected")
logger.error("API call failed", exc_info=True)
```

**Log Levels:**
- `DEBUG`: Development only
- `INFO`: Normal operations
- `WARNING`: Something unexpected but not critical
- `ERROR`: Error occurred but app continues
- `CRITICAL`: App cannot continue

### 2. Health Checks

**Backend Health Endpoint:**
```python
# GET /health
{
    "status": "healthy",
    "timestamp": "2024-01-01T00:00:00Z",
    "checks": {
        "database": "healthy",
        "qdrant": "healthy",
        "minio": "healthy",
        "llm_api": "healthy"
    }
}
```

**Docker Health Check:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 3. Metrics Collection

**Prometheus Metrics (Optional):**
```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)
```

**Metrics to Track:**
- Request rate and latency
- Database query performance
- LLM API call duration
- Document processing time
- Error rates by type

### 4. Error Tracking (Sentry)

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv("APP_ENV", "development")
)
```

## Backup Strategy

### 1. Database Backup

**Automated Backup Script:**
```bash
#!/bin/bash
# backup-db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgres"
DB_NAME="kira_prod"

# Create backup
docker-compose exec -T postgres pg_dump -U kira $DB_NAME > \
    $BACKUP_DIR/kira_$DATE.sql

# Compress
gzip $BACKUP_DIR/kira_$DATE.sql

# Keep last 7 days
find $BACKUP_DIR -name "kira_*.sql.gz" -mtime +7 -delete
```

**Schedule with Cron:**
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup-db.sh
```

### 2. Qdrant Backup

```bash
# Manual backup
docker-compose exec qdrant \
    curl -X POST http://localhost:6333/collections/documents/snapshot

# List snapshots
docker-compose exec qdrant \
    curl http://localhost:6333/collections/documents/snapshots
```

### 3. MinIO Backup

```bash
# Using mc (MinIO Client)
mc mirror minio/kira-docs /backups/minio/

# Schedule daily sync
0 3 * * * mc mirror --overwrite minio/kira-docs /backups/minio/
```

## Security Checklist

### 1. Network Security

- [ ] Firewall configured (only allow necessary ports)
- [ ] HTTPS enabled (SSL/TLS certificates)
- [ ] CORS restricted to specific origins
- [ ] Rate limiting enabled
- [ ] API authentication required

### 2. Application Security

- [ ] Strong secrets (JWT, database passwords)
- [ ] Environment variables not in git
- [ ] Dependency scanning (Snyk, Dependabot)
- [ ] SQL injection prevention (ORM usage)
- [ ] XSS protection (input validation)

### 3. Data Security

- [ ] Database encryption at rest
- [ ] Backup encryption
- [ ] User data isolation (per-user filtering)
- [ ] Sensitive data logging disabled
- [ ] PII data handling compliant

### 4. Infrastructure Security

- [ ] Regular security updates
- [ ] Container vulnerability scanning
- [ ] Least privilege access
- [ ] Audit logging enabled
- [ ] Incident response plan

## Performance Tuning

### 1. Database Optimization

**PostgreSQL Configuration:**
```sql
-- Increase shared buffers
shared_buffers = 4GB

-- Increase work memory for complex queries
work_mem = 256MB

-- Enable query logging
log_min_duration_statement = 1000  # Log queries > 1s

-- Vacuum settings
autovacuum = on
autovacuum_max_workers = 4
```

**Indexes:**
```sql
-- User-specific indexes
CREATE INDEX idx_documents_user ON documents(user_id, created_at DESC);
CREATE INDEX idx_conversations_user ON conversations(user_id, deleted_at);

-- Full-text search
CREATE INDEX idx_documents_fts ON documents USING gin(to_tsvector('vietnamese', content));
```

### 2. Qdrant Optimization

**Collection Configuration:**
```python
# Optimize for performance
qdrant.create_collection(
    collection_name="documents",
    vectors_config={
        "size": 1024,
        "distance": "Cosine"
    },
    optimizers_config={
        "default_segment_number": 4,
        "indexing_threshold": 10000
    },
    replication_factor=2  # For production
)
```

### 3. Application Caching

**Redis Integration (Optional):**
```python
# Cache LLM classifications
@cached(ttl=3600, key_builder=lambda f, q, u: f"classify:{q}:{u}")
async def classify(query: str, user_id: str):
    ...

# Cache retrieval results (short TTL)
@cached(ttl=60, key_builder=lambda f, q, u: f"retrieve:{q}:{u}")
async def retrieve(query: str, user_id: str):
    ...
```

## Troubleshooting

### 1. Common Issues

**Database Connection Failed:**
```bash
# Check PostgreSQL status
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Restart service
docker-compose restart postgres
```

**Qdrant Connection Timeout:**
```bash
# Check Qdrant health
curl http://localhost:6333/

# Restart Qdrant
docker-compose restart qdrant

# Recreate collection
docker-compose exec backend python -m src.scripts.init_qdrant
```

**LLM API Errors:**
```bash
# Check API key
echo $GLM_API_KEY

# Test API connection
curl -X POST https://open.bigmodel.cn/api/paas/v4/chat/completions \
    -H "Authorization: Bearer $GLM_API_KEY" \
    -d '{"model":"glm-4","messages":[{"role":"user","content":"test"}]}'
```

**Frontend Build Failed:**
```bash
# Clear Next.js cache
cd frontend
rm -rf .next

# Reinstall dependencies
npm ci

# Rebuild
npm run build
```

### 2. Log Analysis

**Backend Logs:**
```bash
# View recent logs
docker-compose logs --tail=100 backend

# Follow logs in real-time
docker-compose logs -f backend

# Search for errors
docker-compose logs backend | grep -i error
```

**Database Logs:**
```bash
# PostgreSQL slow queries
docker-compose exec postgres psql -U kira -d kira_dev \
    -c "SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

### 3. Performance Debugging

**Database Query Performance:**
```bash
# Enable query logging
docker-compose exec postgres psql -U kira -d kira_dev \
    -c "ALTER SYSTEM SET log_min_duration_statement = 1000;"

# Reload config
docker-compose exec postgres psql -U kira -d kira_dev -c "SELECT pg_reload_conf();"
```

**API Response Time:**
```python
# Add timing to endpoints
import time

@app.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    start = time.time()

    # ... processing ...

    duration = time.time() - start
    logger.info(f"Request completed in {duration:.2f}s")
```

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing (`pytest`)
- [ ] Code reviewed and merged
- [ ] Database migrations prepared
- [ ] Environment variables configured
- [ ] Backup of current version taken
- [ ] Rollback plan documented

### Deployment

- [ ] Deploy to staging first
- [ ] Run smoke tests on staging
- [ ] Deploy to production (blue-green or canary)
- [ ] Monitor health checks
- [ ] Verify key user flows

### Post-Deployment

- [ ] Monitor error rates (Sentry)
- [ ] Check application logs
- [ ] Verify database performance
- [ ] Monitor LLM API costs
- [ ] Update runbook if needed

## Scaling Strategy

### Vertical Scaling (Scale Up)

**When to use:**
- Small to medium user base (< 1000 users)
- Simple deployment
- Limited budget

**Resources:**
- 16 CPU cores
- 32 GB RAM
- 500 GB SSD

### Horizontal Scaling (Scale Out)

**When to use:**
- Large user base (> 1000 users)
- High availability required
- Predictable traffic patterns

**Architecture:**
```
┌──────────────┐
│   Load       │
│  Balancer    │
└──────┬───────┘
       │
   ┌───┴────┐
   │        │
┌──▼──┐  ┌──▼──┐  ┌──▼──┐
│ App │  │ App │  │ App │  ...
│  1  │  │  2  │  │  3  │
└─────┘  └─────┘  └─────┘
    │        │        │
    └────────┴────────┘
           │
    ┌──────▼──────┐
    │  PostgreSQL │
    │   (Primary) │
    └─────────────┘
```

**Requirements:**
- Sticky sessions for SSE streaming
- Shared session store (Redis)
- External database (managed)
- Centralized logging

## Related Documentation

- [Kiến trúc Hệ thống](./system-architecture.md) - System architecture
- [Hướng dẫn Thiết kế](./design-guidelines.md) - Design principles
- [Lộ trình Phát triển](./project-roadmap.md) - Development roadmap
- [CLAUDE.md](../CLAUDE.md) - Development guidelines
