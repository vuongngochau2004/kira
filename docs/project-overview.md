# Tổng quan Dự án

## Thông tin Project

- **Tên**: K.I.R.A Simplified
- **Mô tả**: Knowledge-based Intelligent Retrieval Assistant - Production-ready RAG system
- **Loại**: Backend API + Frontend Web (Full-stack)
- **Giai đoạn**: Production-ready
- **Version**: 1.0.0

## Tech Stack

### Backend
- **Runtime**: Python 3.12+
- **Framework**: FastAPI
- **LLM**: GLM-4.5 (Zhipu AI), Anthropic Claude, OpenAI GPT
- **LangChain**: LangChain Core cho agent orchestration

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

- [Kiến trúc Hệ thống](./system-architecture.md)
- [Tiêu chuẩn Code](./code-standards.md)
- [Lộ trình Phát triển](./development-roadmap.md)
- [CLAUDE.md](../CLAUDE.md) - Development guidelines chi tiết
