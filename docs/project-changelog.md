# Changelog Dự án

## [1.0.0] - 2024

### Đã thêm

**Backend**
- 4-layer architecture (Serving, Agent/Tools, Retrieval, Ingestion)
- Multi-stage query routing (Quick Filter → LLM Classification → Router Dispatch)
- RAGRouter và ConversationalRouter
- Hybrid retrieval với RRF fusion
- Per-user BM25 indexes
- Intelligent OCR fallback (PyMuPDF → PaddleOCR)
- SSE streaming cho chat responses
- JWT authentication
- Document ingestion pipeline
- LangChain tools integration

**Frontend**
- Next.js 16 App Router setup
- shadcn/ui components
- Zustand state management
- TanStack Query cho API calls
- i18n support (Vietnamese/English)
- Chat interface với streaming
- Document upload components
- Authentication UI (login/register)

**Infrastructure**
- Docker Compose setup
- PostgreSQL 16 + pgvector
- Qdrant vector database
- MinIO object storage
- Migration support

### Đã thay đổi

- N/A (initial release)

### Đã sửa

- N/A (initial release)

### Đã bảo mật

- JWT-based authentication
- Per-user data isolation
- Input validation

## [Unreleased]

### Đã thêm

- Documentation folder (`docs/`)
  - project-overview.md
  - code-standards.md
  - system-architecture.md
  - development-roadmap.md
  - project-changelog.md

---

**Note**: Định dạng này tuân theo [Keep a Changelog](https://keepachangelog.com/) và phiên bản semver [Semantic Versioning](https://semver.org/).
