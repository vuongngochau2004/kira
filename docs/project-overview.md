# Tổng quan Dự án

## Thông tin Project

- **Tên**: K.I.R.A Simplified
- **Mô tả**: Knowledge-based Intelligent Retrieval Assistant - Production-ready RAG system
- **Loại**: Backend API + Frontend Web (Full-stack)
- **Giai đoạn**: Production-ready with SOLID Architecture Refactor (Phase 1 Complete)
- **Version**: 1.0.0

## Tech Stack

### Backend
- **Runtime**: Python 3.12+
- **Framework**: FastAPI
- **LLM**: GLM-4.5 (Zhipu AI), Anthropic Claude, OpenAI GPT
- **LangChain**: LangChain Core cho agent orchestration
- **Architecture**: 4-layer SOLID pattern với Protocol-based design (ABC migration ready)

### Frontend
- **Framework**: Next.js 16 (App Router)
- **Styling**: Tailwind CSS, shadcn/ui (Radix UI)
- **State**: Zustand
- **Data Fetching**: TanStack Query
- **i18n**: next-intl

### Database
- **PostgreSQL**: 16 + pgvector extension
- **Vector DB**: Qdrant
- **Object Storage**: MinIO
- **Search**: Hybrid (Dense + BM25 with RRF)

### Development
- **Testing**: Pytest, pytest-asyncio, pytest-cov
- **Linting**: Ruff, MyPy
- **Build**: Docker Compose

## Team

- **Quy mô**: TBD
- **Methodology**: TBD

## Liên kết nhanh

- [Kiến trúc Hệ thống](./system-architecture.md) - Architecture chi tiết với diagrams
- [Tiêu chuẩn Code](./code-standards.md) - Quy tắc đặt tên, tổ chức file, conventions
- [Tóm tắt Codebase](./codebase-summary.md) - Tổng quan modules, data flows, integration points
- [Hướng dẫn Thiết kế](./design-guidelines.md) - System design principles, patterns, UI/UX guidelines
- [Hướng dẫn Deployment](./deployment-guide.md) - Local setup, production deployment, monitoring
- [Lộ trình Phát triển](./project-roadmap.md) - Milestones, technical debt, changelog
- [CLAUDE.md](../CLAUDE.md) - Development guidelines chi tiết cho AI assistants
