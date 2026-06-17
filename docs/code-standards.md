# Tiêu chuẩn Code

## Quy tắc đặt tên

### Python (Backend)
- **Biến số / Hàm**: `snake_case`
- **Class**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Modules/Files**: `snake_case.py` (ví dụ: `qdrant_store.py`, `chat_handler.py`)
- **Packages/Folders**: `snake_case` (ví dụ: `src/modules/chat/`, `src/shared/adapters/`)

### TypeScript (Frontend)
- **Components**: `PascalCase`
- **Functions/Hooks**: `camelCase`
- **Files**: `kebab-case.tsx` (ví dụ: `DocumentUpload.tsx`, `ChatMessageList.tsx`)
- **Folders**: `kebab-case` (ví dụ: `components/chat/`, `lib/stores/`)

## Tổ chức File

### Backend Structure (Hexagonal Modular Monolith)

```text
src/
├── server/                   # SERVING LAYER - app setup and server-owned HTTP routes
│   ├── main.py              # FastAPI app entrypoint
│   └── api/v1/              # Server-owned API v1 endpoints
│       ├── auth/            # Authentication endpoints
│       ├── evaluation/      # Evaluation endpoints
│       └── metrics/         # Metrics endpoints
│
├── modules/                 # APPLICATION LAYER - Business logic
│   ├── <context>/          # Domain context (e.g., chat, document)
│   │   ├── api/            # Request/Response DTOs (HTTP-specific)
│   │   ├── application/    # Use cases and application DTOs
│   │   ├── domain/         # Domain services, strategies, prompts
│   │   └── infrastructure/ # Module-specific persistence/integration
│   │
│   ├── chat/               # Chat module, including chat API endpoints
│   │   ├── api/
│   │   │   ├── requests.py
│   │   │   └── responses.py
│   │   ├── application/
│   │   │   ├── chat.py           # Chat use case
│   │   │   ├── dto.py            # Application DTOs
│   │   │   └── streaming.py     # SSE streaming logic
│   │   ├── domain/
│   │   │   ├── services/         # Chat domain services
│   │   │   └── prompts/          # Chat prompts
│   │   └── infrastructure/
│   │       └── handlers/         # Chat handlers
│   │           ├── conversational.py
│   │           └── rag_handler.py
│   │
│   ├── classification/      # Classification module
│   │   ├── api/
│   │   ├── application/
│   │   └── domain/
│   │       ├── cache/
│   │       └── strategies/
│   │           ├── cached.py
│   │           ├── composite.py
│   │           ├── keyword.py
│   │           └── llm.py
│   │
│   ├── document/            # Document module, including document API endpoints
│   │   ├── api/
│   │   ├── application/
│   │   │   ├── upload.py
│   │   │   ├── delete.py
│   │   │   └── process.py
│   │   ├── domain/
│   │   └── infrastructure/
│   │
│   ├── retrieval/           # Retrieval module
│   │   ├── api/
│   │   ├── application/
│   │   ├── domain/
│   │   │   └── services/
│   │   └── infrastructure/
│   │       ├── vector/
│   │       ├── keyword/
│   │       └── document_store/
│   │
│   ├── evaluation/          # Evaluation module
│   │   ├── api/
│   │   ├── application/
│   │   └── domain/
│   │
│   └── rag/                 # RAG module
│       ├── application/
│       ├── domain/
│       │   ├── services/
│       │   ├── prompts/
│       │   └── __init__.py
│       ├── orchestration/
│       └── infrastructure/
│
├── shared/                  # SHARED LAYER - Cross-cutting concerns
│   ├── ports/              # External system interfaces (ABC)
│   │   ├── llm.py          # LLM client interface
│   │   ├── vector_store.py # Vector store interface
│   │   ├── embedding.py    # Embedding service interface
│   │   ├── ocr.py          # OCR service interface
│   │   └── storage.py      # Storage interface
│   │
│   ├── adapters/           # External system implementations
│   │   ├── llm/
│   │   │   ├── glm.py
│   │   │   ├── gemini.py
│   │   │   └── openai.py
│   │   ├── vector/
│   │   │   └── qdrant.py
│   │   ├── embedding/
│   │   │   └── api_client.py
│   │   ├── ocr/
│   │   │   └── paddleocr.py
│   │   └── storage/
│   │       └── minio.py
│   │
│   ├── infrastructure/      # Technical infrastructure
│   │   ├── auth/
│   │   │   └── jwt.py
│   │   ├── llm/
│   │   │   └── client.py
│   │   ├── monitoring/
│   │   ├── persistence/
│   │   │   └── database/
│   │   │       ├── session.py
│   │   │       └── models.py
│   │   └── logging/
│   │
│   ├── kernel/             # DI and service registry
│   │   ├── base/           # Base interfaces
│   │   ├── di/
│   │   │   ├── container.py
│   │   │   └── registry.py
│   │   └── utils/
│   │
│   ├── domain/             # Shared domain entities
│   │   ├── entities/
│   │   └── value_objects/
│   │
│   └── utils/              # Utility functions
│
├── config/                  # Configuration
│   ├── config.py           # Pydantic settings (env-based)
│   └── settings.yaml       # Static configuration
│
├── constants/               # Application constants
│   └── __init__.py
│
└── tools/                   # Tool initialization (legacy)
    ├── retrieval_tools.py
    └── ingestion_tools.py
```

**Key Principles:**

1. **Module Boundaries**: Each module is self-contained with api/application/domain/infrastructure
2. **Shared Layer**: Cross-cutting concerns live in shared/ with clear ports/adapters separation
3. **Serving Layer**: HTTP concerns only in server/api/
4. **DI Container**: Service wiring in shared/kernel/di/

### Frontend Structure

```text
frontend/src/
├── app/                    # Next.js App Router
│   ├── login/
│   │   └── page.tsx
│   ├── register/
│   │   └── page.tsx
│   ├── conversation/
│   │   └── [id]/
│   │       └── page.tsx
│   ├── conversations/
│   │   └── page.tsx
│   ├── uploads/
│   │   └── page.tsx
│   ├── layout.tsx
│   ├── page.tsx           # Home page
│   └── globals.css
│
├── components/             # UI components
│   ├── ui/                # shadcn/ui components
│   ├── auth/              # Auth-specific components
│   ├── simple/            # Simple chat and document panel components
│   ├── streaming/         # Streaming and citation components
│   ├── sources/           # Source panel components
│   ├── sidebar/           # Sidebar components
│   └── common/            # Shared components
│
├── lib/                    # Client code and state
│   ├── api/               # API clients
│   │   └── simple-client.ts
│   ├── hooks/             # Custom hooks
│   │   ├── use-simple-chat.ts
│   │   └── use-streaming-chat.ts
│   ├── stores/            # Zustand stores
│   │   ├── auth-store.ts
│   │   ├── conversation-store.ts
│   │   └── sources-store.ts
│   ├── streaming/         # Streaming helpers
│   │   ├── index.ts
│   │   └── streaming-state-builder.ts
│   ├── locales/           # Locale files
│   └── utils/             # Utility functions
│
```

## Architecture Patterns

### Hexagonal Architecture Principles

**Inside (Application Core):**
- `src/modules/` - Business logic, use cases, domain services
- `src/shared/domain/` - Shared entities and value objects
- `src/shared/ports/` - Interfaces for external services

**Outside (Infrastructure):**
- `src/shared/adapters/` - External service implementations
- `src/shared/infrastructure/` - Technical infrastructure (DB, auth, monitoring)
- `src/server/` - HTTP serving layer

**Key Rules:**
1. **Inside** defines interfaces (ports), **Outside** implements them (adapters)
2. **Modules** contain business logic, **Server** contains HTTP concerns only
3. **Domain** in modules owns business rules, **Application** orchestrates use cases
4. **Infrastructure** in shared layer handles technical concerns
5. All dependencies point inward (toward the domain)

### Module Structure Pattern

Each module follows this structure:

```text
src/modules/<context>/
├── api/                    # HTTP-specific DTOs
├── application/            # Use cases (orchestration)
├── domain/                 # Domain logic (business rules)
└── infrastructure/         # Module-specific persistence/integration
```

**Responsibilities:**
- `api/`: Request/response models for HTTP endpoints
- `application/`: Use case orchestration, application DTOs
- `domain/`: Domain services, strategies, business rules
- `infrastructure/`: Module-specific persistence, external integration

### Key Patterns

#### 1. Strategy Pattern
**Usage**: Pluggable classification strategies
```python
# src/modules/classification/domain/strategies/
class ClassificationStrategy(ABC):
    @abstractmethod
    async def classify(self, query: str, user_id: str) -> ClassificationResult:
        pass

class KeywordStrategy(ClassificationStrategy):
    async def classify(self, query: str, user_id: str) -> ClassificationResult:
        # Keyword matching logic
        pass

class LLMStrategy(ClassificationStrategy):
    async def classify(self, query: str, user_id: str) -> ClassificationResult:
        # LLM-based classification
        pass
```

#### 2. Port-Adapter Pattern
**Usage**: External service integration
```python
# src/shared/ports/llm.py (Interface)
class LLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass

# src/shared/adapters/llm/glm.py (Implementation)
class GLMClient(LLMClient):
    async def generate(self, prompt: str) -> str:
        # GLM-specific implementation
        pass
```

#### 3. Dependency Injection
**Usage**: Service wiring through DI container
```python
# src/shared/kernel/di/container.py
class ServiceContainer:
    def register_chat_handler(self, handler: ChatHandler):
        self._services[ChatHandler] = handler

    def get_chat_handler(self) -> ChatHandler:
        return self._services[ChatHandler]
```

#### 4. Repository Pattern
**Usage**: Data access abstraction
```python
# src/modules/retrieval/infrastructure/dense.py
class DenseRetrievalRepository:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    async def search(self, query_vector: list[float], user_id: str):
        return await self.vector_store.search(query_vector, filter={"user_id": user_id})
```

#### 5. Factory Pattern
**Usage**: Handler creation
```python
# src/modules/chat/application/chat.py
class ChatFactory:
    @staticmethod
    def create_handler(classification: ClassificationResult) -> QueryHandler:
        if classification.intent == Intent.RAG:
            return RAGHandler()
        return ConversationalHandler()
```

### Async-First Pattern

**Rule**: All I/O operations MUST be async

```python
# ✅ GOOD: Async I/O
async def fetch_documents(user_id: str) -> list[Document]:
    return await db.execute(select(Document).where(Document.user_id == user_id))

# ❌ BAD: Sync I/O (blocks event loop)
def fetch_documents(user_id: str) -> list[Document]:
    return db.execute(select(Document).where(Document.user_id == user_id))
```

### Per-User Isolation Pattern

**Rule**: All data MUST be scoped by `user_id`

```python
# ✅ GOOD: User-scoped operations
async def get_user_documents(user_id: str) -> list[Document]:
    return await qdrant_store.search(query, filter={"user_id": user_id})

# ❌ BAD: Cross-user access
async def get_all_documents() -> list[Document]:
    return await qdrant_store.search(query)  # Returns all users' data!
```

## Quy ước Git

### Branch Strategy
- Main branch: `main`
- Feature branches: `feat/<description>`
- Bugfix branches: `fix/<description>`
- Refactor branches: `refactor/<description>`

### Commit Messages

Sử dụng Conventional Commits:

```
type(scope): description

# Types:
feat:     New feature
fix:      Bug fix
docs:     Documentation changes
refactor: Code refactoring (no functional change)
test:     Test additions/changes
chore:    Maintenance tasks
perf:     Performance improvements
style:    Code style changes (formatting, etc.)

# Examples:
feat(chat): add streaming response support
fix(auth): resolve JWT token expiration issue
docs(readme): update setup instructions
refactor(modules): extract document ingestion logic
test(retrieval): add hybrid retrieval tests
chore(deps): upgrade dependencies
```

### Code Review
- Bắt buộc cho tất cả changes
- Tối thiểu 1 approval
- CI checks phải pass
- No merge conflicts

## Best Practices

### Backend

#### Type Hints
```python
# ✅ GOOD: Complete type hints
async def search_documents(
    query: str,
    user_id: str,
    limit: int = 5
) -> list[Document]:
    """Search documents for a user."""
    return await repository.search(query, user_id, limit)

# ❌ BAD: Missing type hints
async def search_documents(query, user_id, limit=5):
    return await repository.search(query, user_id, limit)
```

#### Docstrings
```python
# ✅ GOOD: Clear docstring
class RAGHandler:
    """Handler for RAG queries with retrieval-augmented generation.
    
    This handler executes the full RAG pipeline:
    1. Classify query intent
    2. Retrieve relevant documents
    3. Generate response with context
    4. Extract citations
    """
    
    async def handle(self, query: str, user_id: str) -> HandlerResult:
        """Execute RAG pipeline.
        
        Args:
            query: User query string
            user_id: User identifier for data isolation
            
        Returns:
            HandlerResult with response and citations
            
        Raises:
            RetrievalError: If document retrieval fails
            GenerationError: If LLM generation fails
        """
        pass

# ❌ BAD: No docstring
class RAGHandler:
    async def handle(self, query, user_id):
        pass
```

#### Error Handling
```python
# ✅ GOOD: Structured error handling
try:
    result = await llm_client.generate(prompt)
except APIError as e:
    logger.error(f"LLM API error: {e}", exc_info=True)
    raise GenerationError(f"Failed to generate response: {e}") from e
except TimeoutError as e:
    logger.warning(f"LLM timeout: {e}")
    raise GenerationError("Response generation timed out") from e

# ❌ BAD: Silent errors
try:
    result = await llm_client.generate(prompt)
except:
    pass  # Swallows all errors!
```

#### Logging
```python
# ✅ GOOD: Structured logging with context
logger.info(
    "Document upload started",
    extra={
        "user_id": user_id,
        "filename": filename,
        "file_size": file_size
    }
)

# ❌ BAD: Unstructured logging
logger.info(f"User {user_id} uploaded {filename}")
```

### Frontend

#### TypeScript Strict Mode
```typescript
// ✅ GOOD: Proper typing
interface Document {
  id: string;
  filename: string;
  status: 'processing' | 'completed' | 'failed';
  createdAt: Date;
}

const useDocuments = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  // ...
};

// ❌ BAD: Any types
const useDocuments = () => {
  const [documents, setDocuments] = useState<any>([]);
  // ...
};
```

#### Component Composition
```typescript
// ✅ GOOD: Composed components
<ChatMessageList>
  <ChatMessage role="user" content="Hello" />
  <ChatMessage role="assistant" content="Hi there" />
</ChatMessageList>

// ❌ BAD: Monolithic component
<ChatInterface messages={[...]} />
```

#### Error Boundaries
```typescript
// ✅ GOOD: Error boundary
<ErrorBoundary fallback={<ErrorAlert />}>
  <ChatInterface />
</ErrorBoundary>

// ❌ BAD: No error handling
<ChatInterface />
```

#### Loading States
```typescript
// ✅ GOOD: Loading states
const { data, isLoading, error } = useDocuments();

if (isLoading) return <DocumentListSkeleton />;
if (error) return <ErrorAlert message={error.message} />;
return <DocumentList documents={data} />;

// ❌ BAD: No loading state
const { data } = useDocuments();
return <DocumentList documents={data} />;
```

## Vietnamese Language Support

### Embedding
- Model: Vietnamese-embedding-v2 or BAAI/bge-m3
- Dimension: 1024
- Preserve Vietnamese diacritics in text cleaning

### OCR
- PaddleOCR with Vietnamese language model
- Fallback: PyMuPDF native extraction

### LLM
- Primary: GLM-4.5 (strong Vietnamese support)
- Backup: Claude, GPT-4

### Text Processing
```python
# ✅ GOOD: Preserve diacritics
def clean_text(text: str) -> str:
    # Remove excess whitespace but keep diacritics
    return re.sub(r'\s+', ' ', text).strip()

# ❌ BAD: Remove diacritics
def clean_text(text: str) -> str:
    # This would remove Vietnamese accents!
    return unidecode(text)
```

## Testing Guidelines

### Backend Tests

```python
# ✅ GOOD: Clear test structure
@pytest.mark.asyncio
async def test_rag_handler_with_valid_query():
    """Test RAG handler returns response with citations."""
    # Arrange
    handler = RAGHandler(mock_retrieval, mock_llm)
    query = "What is the document about?"
    user_id = "test-user"
    
    # Act
    result = await handler.handle(query, user_id)
    
    # Assert
    assert result.response is not None
    assert len(result.citations) > 0
    assert result.confidence > 0.7

# ❌ BAD: Unclear test
async def test_handler():
    handler = RAGHandler()
    result = await handler.handle("test", "user")
    assert result is not None
```

### Frontend Tests

```typescript
// ✅ GOOD: Clear test with assertions
test('document upload displays success message', async ({ page }) => {
  await page.goto('/uploads');
  const fileInput = page.locator('[data-testid="file-input"]');
  
  await fileInput.setInputFiles('test.pdf');
  await page.click('[data-testid="upload-button"]');
  
  await expect(page.locator('[data-testid="success-toast"]')).toBeVisible();
  await expect(page.locator('[data-testid="success-toast"]')).toContainText('Upload thành công');
});

// ❌ BAD: Vague assertions
test('upload works', async ({ page }) => {
  await page.goto('/uploads');
  // ... upload logic
  expect(true).toBe(true);
});
```

## Code Quality Tools

### Backend
- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checker
- **Pytest**: Testing framework
- **pytest-cov**: Coverage reporting

### Frontend
- **ESLint**: JavaScript/TypeScript linter
- **Prettier**: Code formatter
- **TypeScript**: Type checking
- **Vitest/Jest**: Testing framework

### Pre-commit Hooks
```bash
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
```

## Related Documentation

- [Kiến trúc Hệ thống](./system-architecture.md) - Architecture patterns
- [Tổng quan Dự án](./project-overview.md) - Project structure and runtime overview
- [CLAUDE.md](../CLAUDE.md) - Development guidelines

---

*Last Updated: 2026-06-12*
*Architecture: Hexagonal Modular Monolith*
*Python: 3.12 | TypeScript: 5.x*
