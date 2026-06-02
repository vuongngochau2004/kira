# Tiêu chuẩn Code

## Quy tắc đặt tên

### Python (Backend)
- **Biến số / Hàm**: `snake_case`
- **Class**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Modules/Files**: `kebab-case.py` (ví dụ: `paddleocr_client.py`)

### TypeScript (Frontend)
- **Components**: `PascalCase`
- **Functions/Hooks**: `camelCase`
- **Files**: `kebab-case.tsx` (ví dụ: `DocumentUpload.tsx`)

## Tổ chức File

### Backend Structure
```
src/
├── api/              # SERVING LAYER - HTTP endpoints
├── agents/           # AGENT LAYER - Routing & LLM logic
│   └── routers/      # Router implementations
├── tools/            # LangChain tools (@tool decorator)
├── retrieval/        # RETRIEVAL LAYER - Search algorithms
├── indexing/         # INDEXING LAYER - DB clients
├── ingestion/        # INGESTION LAYER - ETL pipeline
├── auth/             # JWT authentication
├── database/         # SQLAlchemy models
├── models/           # Pydantic schemas
└── constants/        # Application constants
```

### Frontend Structure
```
frontend/src/
├── app/              # Next.js App Router
├── components/       # UI components
│   ├── auth/
│   ├── common/
│   ├── sidebar/
│   └── ...
├── lib/
│   ├── api/          # API clients
│   ├── hooks/        # Custom hooks
│   └── stores/       # Zustand stores
└── ...
```

## Architecture Patterns

### 4-Layer Pattern
1. **SERVING** (`src/api/`): HTTP concerns only
2. **AGENT/TOOLS** (`src/agents/`, `src/tools/`): Business logic
3. **RETRIEVAL** (`src/retrieval/`, `src/indexing/`): Data access
4. **INGESTION** (`src/ingestion/`): ETL pipeline

### Key Patterns
- **Per-User Isolation**: BM25 indexes, documents, conversations scoped to `user_id`
- **Async-First**: All I/O use async/await
- **LangChain Tools**: `@tool` decorators for agent integration
- **SSE Streaming**: Structured chunks for real-time responses
- **Soft Delete**: Conversations use `deleted_at` timestamp

## Quy ước Git

### Branch Strategy
- Main branch: `main`
- Feature branches: TBD

### Commit Messages
- Sử dụng Conventional Commits
- Format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Code Review
- Bắt buộc cho tất cả changes
- Reviewer: TBD

## Best Practices

### Backend
- Type hints cho tất cả functions
- Docstrings cho modules và complex functions
- Error handling với structured errors
- Logging với appropriate levels

### Frontend
- TypeScript strict mode
- Component composition patterns
- Proper error boundaries
- Loading states và optimistic updates

## Vietnamese Language Support

- Embeddings: BAAI/bge-m3 hoặc Vietnamese-embedding-v2
- OCR: PaddleOCR với Vietnamese language model
- LLM: GLM-4.5 (strong Vietnamese support)
- Text cleaning: Preserve Vietnamese diacritics
