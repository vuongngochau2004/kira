# Lộ trình Phát triển

## Giai đoạn hiện tại

**Status**: Production-ready with Hexagonal Modular Monolith Architecture (Complete)

Dự án đã hoàn thành core features và major architectural refactoring:
- ✅ Hexagonal Modular Monolith Architecture
  - ✅ Module structure: chat, classification, document, evaluation, rag, retrieval
  - ✅ Shared layer: ports, adapters, infrastructure, kernel, domain
  - ✅ Serving layer: server with API v1 endpoints
- ✅ Hybrid Retrieval System (Dense + BM25 with RRF)
- ✅ Per-user data isolation
- ✅ Intelligent query classification (Strategy pattern)
- ✅ Agentic RAG with LangGraph
- ✅ SSE streaming responses
- ✅ JWT authentication with httpOnly cookies
- ✅ Frontend (Next.js 16 + React 19 + shadcn/ui)
- ✅ Evaluation system (DeepEval integration)

## Recent Achievements (2026)

### Hexagonal Architecture Migration ✅ COMPLETE (2026-06-12)

**Completed:**
- ✅ Module structure established (6 modules)
- ✅ Shared layer created (ports, adapters, infrastructure, kernel, domain)
- ✅ Serving layer separated (server with API endpoints)
- ✅ DI container implemented
- ✅ Documentation updated

**Module Breakdown:**
```
src/modules/
├── chat/           # Chat use cases, handlers, streaming
├── classification/ # Query routing strategies
├── document/       # Document upload and ingestion
├── evaluation/     # DeepEval evaluation services
├── rag/            # Agentic RAG, LangGraph
└── retrieval/      # Dense, BM25, hybrid search

src/shared/
├── ports/          # External system interfaces
├── adapters/       # External system implementations
├── infrastructure/ # Technical concerns (auth, DB, monitoring)
├── kernel/         # DI container, registry
└── domain/         # Shared entities, value objects

src/server/
└── api/v1/         # HTTP endpoints
    ├── auth/
    ├── chat/
    ├── documents/
    ├── evaluation/
    └── metrics/
```

## Các milestones sắp tới

### Milestone 1: Testing & Quality 🔴 HIGH PRIORITY

**Objectives:**
- Achieve 70%+ test coverage
- Establish CI/CD pipeline
- Add integration tests

**Tasks:**
- [ ] Unit tests for core modules
  - [ ] Chat module tests
  - [ ] Classification module tests
  - [ ] Retrieval module tests
  - [ ] Document module tests
  - [ ] Evaluation module tests
  - [ ] RAG module tests
- [ ] Integration tests for API endpoints
  - [ ] Auth endpoints
  - [ ] Chat endpoints
  - [ ] Document endpoints
  - [ ] Evaluation endpoints
- [ ] E2E tests for critical flows
  - [ ] Document upload → search → chat flow
  - [ ] Authentication flow
  - [ ] Conversation management
- [ ] CI/CD pipeline setup
  - [ ] GitHub Actions workflow
  - [ ] Automated testing on PR
  - [ ] Automated deployment
- [ ] Code quality gates
  - [ ] Ruff linting
  - [ ] MyPy type checking
  - [ ] Coverage thresholds

**Success Criteria:**
- 70%+ test coverage
- All tests pass in CI
- PR checks enforced

**Estimated Time:** 3-4 weeks

### Milestone 2: Performance Optimization 🟡 MEDIUM PRIORITY

**Objectives:**
- Improve response times
- Optimize database queries
- Add caching layer

**Tasks:**
- [ ] Database optimization
  - [ ] Query profiling and optimization
  - [ ] Index tuning
  - [ ] Connection pooling optimization
- [ ] Caching strategy
  - [ ] Redis integration for classification cache
  - [ ] LLM response caching (where appropriate)
  - [ ] Query result caching (short TTL)
- [ ] Vector search optimization
  - [ ] Qdrant collection tuning
  - [ ] Payload indexing
  - [ ] HNSW parameters optimization
- [ ] Frontend performance
  - [ ] Bundle size optimization
  - [ ] Lazy loading for components
  - [ ] Image optimization

**Success Criteria:**
- Chat streaming latency < 2s first token
- Document upload processing < 10s for 10MB PDF
- Search queries < 500ms p95
- Frontend Lighthouse score > 90

**Estimated Time:** 2-3 weeks

### Milestone 3: Production Readiness 🟢 NORMAL PRIORITY

**Objectives:**
- Production deployment setup
- Monitoring and alerting
- Security hardening

**Tasks:**
- [ ] Production deployment
  - [ ] Managed PostgreSQL (RDS/CloudSQL)
  - [ ] Managed Qdrant (cloud or optimized self-hosted)
  - [ ] Managed MinIO or S3-compatible storage
  - [ ] CDN for frontend assets
- [ ] Monitoring & logging
  - [ ] Application metrics (Prometheus/Grafana)
  - [ ] Log aggregation (ELK/Loki)
  - [ ] Error tracking (Sentry)
  - [ ] Uptime monitoring
- [ ] Security
  - [ ] Security audit
  - [ ] Dependency scanning (Snyk/Dependabot)
  - [ ] Rate limiting
  - [ ] API key rotation process
  - [ ] SSL/TLS hardening
- [ ] Backup & disaster recovery
  - [ ] Automated database backups
  - [ ] Qdrant snapshot backups
  - [ ] MinIO replication
  - [ ] Disaster recovery procedure

**Success Criteria:**
- 99.9% uptime target
- < 5min recovery time objective (RTO)
- < 1hr recovery point objective (RPO)
- Security audit passed

**Estimated Time:** 3-4 weeks

### Milestone 4: Features Enhancement 🔵 LOW PRIORITY

**Objectives:**
- Add advanced RAG techniques
- Improve user experience
- Add export capabilities

**Tasks:**
- [ ] Advanced RAG techniques
  - [ ] Query expansion
  - [ ] HyDE (Hypothetical Document Embeddings)
  - [ ] Re-ranking with cross-encoders
  - [ ] Multi-query fusion
- [ ] Multi-modal support
  - [ ] Image extraction from documents
  - [ ] Image captioning for context
  - [ ] Multi-modal queries
- [ ] User experience improvements
  - [ ] Export/import conversations
  - [ ] Share conversations (public link)
  - [ ] Advanced search filters
  - [ ] Document tagging and organization
  - [ ] Batch document operations
- [ ] Collaboration features
  - [ ] Shared workspaces
  - [ ] Document sharing between users
  - [ ] Comments on documents

**Success Criteria:**
- At least 2 advanced RAG techniques implemented
- Export/import functionality working
- User feedback positive on new features

**Estimated Time:** 4-6 weeks

## Nợ kỹ thuật

### High Priority 🔴
- [ ] Complete test coverage (current: ~0%)
- [ ] Add API rate limiting
- [ ] Implement request tracing (OpenTelemetry)
- [ ] Add comprehensive logging structure

### Medium Priority 🟡
- [ ] Error handling refinement
- [ ] Add retry logic for external APIs
- [ ] Implement graceful degradation
- [ ] Add health check endpoints for all services

### Low Priority 🟢
- [ ] Remove legacy code comments
- [ ] Optimize bundle size
- [ ] Add more language support (i18n)
- [ ] Improve accessibility (a11y)

## Architecture Debt

### Resolved ✅
- ~~Monolithic structure~~ → Hexagonal modular monolith implemented
- ~~Mixed responsibilities~~ → Clear module boundaries established
- ~~Tight coupling to external services~~ → Port-adapters pattern implemented
- ~~No dependency injection~~ → DI container implemented

### Remaining 🟡
- [ ] Feature flags need cleanup (some not used)
- [ ] Some modules could be further split
- [ ] Protocol vs ABC choice needs consistency
- [ ] Domain model could be richer

## Technical Stack Updates

### Considered Upgrades
- [ ] Python 3.13 (when stable)
- [ ] Next.js 17 (when available)
- [ ] React 19.1+ (when available)
- [ ] Upgrade to FastAPI 0.115+

### External Services
- [ ] Evaluate alternative embedding services
- [ ] Consider managed vector DB options
- [ ] Evaluate alternative LLM providers

## Research & Exploration

### Active Research Areas
- [ ] Advanced RAG techniques evaluation
- [ ] Multi-modal RAG approaches
- [ ] Knowledge graph integration
- [ ] Fine-tuning embedding models

### Future Possibilities
- [ ] GraphRAG implementation
- [ ] Local LLM integration (Ollama)
- [ ] Voice query support
- [ ] Real-time collaboration

## Dependencies

### External Dependencies Status
- **GLM-4.5**: Stable, primary LLM
- **Qdrant**: Stable, vector DB
- **PostgreSQL 16**: Stable, metadata store
- **Next.js 16**: Stable, frontend framework
- **PaddleOCR**: Stable, OCR fallback

### Dependency Health
- [ ] Regular dependency updates (monthly)
- [ ] Security scanning (Snyk)
- [ ] License compliance check
- [ ] Deprecation monitoring

## Liên kết

- [Kiến trúc Hệ thống](./system-architecture.md) - Architecture chi tiết
- [Tiêu chuẩn Code](./code-standards.md) - Code conventions
- [Tổng quan Dự án](./project-overview.md) - Project overview
- [Hướng dẫn Deployment](./deployment-guide.md) - Deployment guide
- [CLAUDE.md](../CLAUDE.md) - Development guidelines

---

*Last Updated: 2026-06-12*
*Current Phase: Production-ready*
*Next Priority: Testing & Quality*
