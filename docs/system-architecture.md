# Kiến trúc Hệ thống

## Tổng quan Architecture

K.I.R.A Simplified theo **4-layer architecture pattern** với tách biệt rõ ràng giữa các lớp, và đã được refactor theo **SOLID principles** với protocol-based design:

```mermaid
graph TB
    subgraph Clients["Client Layer"]
        WebUI[Web UI<br/>Next.js 16]
        APIKey[API Client]
    end

    subgraph Serving["Serving Layer (src/api/)"]
        FastAPI[FastAPI Server]
        AuthJWT[JWT Auth Middleware]
        SSE[SSE Streaming]
        AuthEP[Auth Endpoints]
        DocEP[Document Endpoints]
        ChatEP[Chat Endpoints]
    end

    subgraph AgentLayer["Agent/Tools Layer (src/agents/)"]
        Orchestrator[OrchestratorAgent]
        RouterRegistry[RouterRegistry]
        QueryClassifier[QueryClassifier]
        subgraph Routers["Routers"]
            RAGRouter[RAGRouter]
            ConvRouter[ConversationalRouter]
        end
        AgenticRAG[AgenticRAG Agent]
        LLMClient[LLM Client]
    end

    subgraph Tools["Tools Layer (src/tools/)"]
        RetrievalTools[retrieval_tools.py]
        IngestionTools[ingestion_tools.py]
    end

    subgraph Retrieval["Retrieval Layer"]
        DenseRetrieval[dense.py<br/>Vector Search]
        BM25Retrieval[bm25.py<br/>Keyword Search]
        HybridRetrieval[hybrid.py<br/>RRF Fusion]
    end

    subgraph Indexing["Indexing Layer"]
        QdrantStore[qdrant_store.py]
        DocStore[document_store.py]
        FileStore[file_store.py]
    end

    subgraph Ingestion["Ingestion Layer"]
        Extractor[extractor.py<br/>OCR Fallback]
        PaddleOCR[paddleocr_client.py]
        Cleaner[cleaner.py]
        Chunker[chunker.py]
        Embedding[embedding.py]
        BM25Builder[bm25_builder.py]
        Pipelines[pipelines.py]
    end

    subgraph Storage["External Storage"]
        QdrantDB[(Qdrant<br/>Vector DB)]
        PGDB[(PostgreSQL<br/>Metadata)]
        MinIO[(MinIO<br/>Files)]
        LLMService[(LLM API<br/>GLM/Claude/GPT)]
        EmbedAPI[(Embedding API<br/>Vietnamese)]
    end

    WebUI --> FastAPI
    APIKey --> FastAPI
    FastAPI --> AuthJWT
    AuthJWT --> AuthEP
    AuthJWT --> DocEP
    AuthJWT --> ChatEP
    ChatEP --> SSE
    SSE --> Orchestrator
    Orchestrator --> RouterRegistry
    RouterRegistry --> QueryClassifier
    RouterRegistry --> Routers
    Routers --> AgenticRAG
    AgenticRAG --> LLMClient
    LLMClient --> LLMService
    RAGRouter --> RetrievalTools
    RetrievalTools --> DenseRetrieval
    RetrievalTools --> BM25Retrieval
    DenseRetrieval --> HybridRetrieval
    BM25Retrieval --> HybridRetrieval
    HybridRetrieval --> QdrantStore
    QdrantStore --> QdrantDB
    HybridRetrieval --> DocStore
    DocStore --> PGDB
    DocEP --> IngestionTools
    IngestionTools --> Pipelines
    Pipelines --> Extractor
    Extractor --> PaddleOCR
    Pipelines --> Cleaner
    Pipelines --> Chunker
    Pipelines --> Embedding
    Pipelines --> BM25Builder
    Pipelines --> QdrantStore
    Embedding --> EmbedAPI
    Chunker --> BM25Builder
    FileStore --> MinIO
    Extractor --> FileStore
```

## Các thành phần chính

### 1. SOLID Protocol-Based Architecture (Refactor mới)

```mermaid
graph TB
    subgraph Protocols["Protocol Layer (src/protocols/)"]
        ClassProtocol[ClassificationStrategy<br/>Protocol]
        HandlerProtocol[QueryHandler<br/>Protocol]
        RetrieverProtocol[Retriever<br/>Protocol]
        ContainerProtocol[DependencyContainer<br/>Protocol]
    end

    subgraph Classification["Classification Layer (src/classification/)"]
        Composite[CompositeClassifier<br/>Fallback Chain]
        Keyword[KeywordStrategy<br/>&lt;5ms]
        Cached[CachedStrategy<br/>LRU Cache]
        LLMClass[LLMStrategy<br/>~800ms]
    end

    subgraph Handlers["Handler Layer (src/handlers/)"]
        RAGHandler[RAGHandler<br/>Retrieval + Generation]
        ConvHandler[ConversationalHandler<br/>Direct Chat]
        Adapter[RouterAdapter<br/>Legacy Support]
    end

    subgraph DI["DI Layer (src/di/)"]
        Container[ServiceContainer<br/>Lifecycle Management]
        Registry[ServiceRegistry<br/>Service Registration]
        FeatureFlags[FeatureFlagManager<br/>Percentage Rollout]
    end

    Protocols --> Classification
    Protocols --> Handlers
    Protocols --> DI

    Composite --> Keyword
    Composite --> Cached
    Cached --> LLMClass

    RAGHandler --> RetrieverProtocol
    Adapter --> HandlerProtocol

    Container --> ContainerProtocol
    Registry --> Container
    FeatureFlags --> Container

    style Protocols fill:#e1f5fe
    style Classification fill:#c8e6c9
    style Handlers fill:#ffecb3
    style DI fill:#f3e5f5
```

**Protocol Benefits**:
- **DIP**: High-level modules depend on protocols, not concretions
- **OCP**: Open for extension (new implementations), closed for modification
- **SRP**: Single responsibility - handlers execute, classifiers classify
- **Testability**: Protocol-based mocking in tests

### 2. Multi-Agent Routing (Legacy → Protocol Migration)

```mermaid
flowchart TD
    subgraph Stage1["Stage 1: Quick Filter"]
        QueryInput[User Query + User ID]
        FileMatch{Fuzzy File<br/>Matching}
        FileMatch -->|Filename Found| RAGPath1
        FileMatch -->|No Match| KeywordCheck{File Keywords?}
        KeywordCheck -->|Has Keywords| RAGPath1
        KeywordCheck -->|No Keywords| RouterCheck{Router<br/>Confidence}
        RouterCheck -->|> 80%| DirectPath[Direct Route]
        RouterCheck -->|< 80%| Stage2
    end

    subgraph Stage2["Stage 2: LLM Classification"]
        Classify[QueryClassifier<br/>LLM-Based]
        Intent{Intent<br/>Detection}
        Intent -->|RAG Intent| RAGPath2
        Intent -->|Chat Intent| ConvPath
        Intent -->|Uncertain| DefaultPath[Default RAG]
        Intent -->|Low Confidence| DefaultPath
    end

    subgraph Stage3["Stage 3: Router Dispatch"]
        RAGPath1[RAGRouter]
        RAGPath2[RAGRouter]
        DirectPath[RAGRouter]
        ConvPath[ConversationalRouter]
        DefaultPath[RAGRouter]
        RAGPath1 --> RAGExecution
        RAGPath2 --> RAGExecution
        DirectPath --> RAGExecution
        DefaultPath --> RAGExecution
        ConvPath --> ConvExecution
    end

    subgraph RAGExecution["RAG Execution"]
        Retrieval[Hybrid Retrieval<br/>Dense + BM25]
        ContextBuild[Context Building]
        LLMGen[LLM Generation<br/>with Citations]
        Retrieval --> ContextBuild
        ContextBuild --> LLMGen
    end

    subgraph ConvExecution["Conversational Execution"]
        DirectLLM[Direct LLM Chat<br/>No Retrieval]
    end

    LLMGen --> Response
    DirectLLM --> Response
    QueryInput --> FileMatch
    RAGPath1 --> RAGExecution
```

**Stages:**

1. **Quick Filter**: Fuzzy filename matching + keyword detection
2. **LLM Classification**: Intent detection (RAG vs Conversational)
3. **Router Dispatch**: Route to appropriate handler

**New Architecture (Protocol-based)**:

- Classification moved to `src/classification/` with Strategy pattern
- Handlers moved to `src/handlers/` with QueryHandler protocol
- RouterAdapter provides backward compatibility with old routers

### 3. Classification Chain (Strategy Pattern)

### 4. Hybrid Retrieval (RRF)

- **Dense**: Vector similarity search via Qdrant
- **BM25**: Keyword search per-user index
- **RRF**: Reciprocal Rank Fusion for result merging

### 5. Intelligent OCR Fallback

- PyMuPDF native text extraction
- Low-quality detection → PaddleOCR fallback
- 2D layout sorting for reading order

## Luồng dữ liệu

### Query Processing Flow (Legacy)

1. User query → FastAPI `/chat/stream`
2. Orchestrator: Quick Filter → LLM Classification → Router Dispatch
3. RAGRouter: Hybrid Retrieval (Dense + BM25)
4. Context Building + LLM Generation
5. SSE Streaming response

### Query Processing Flow (New Protocol-Based)

1. User query → FastAPI `/chat/stream`
2. **Classification**: CompositeClassifier tries strategies in order
   - KeywordStrategy → CachedStrategy → LLMStrategy
   - Returns ClassificationResult with intent + confidence
3. **Handler Selection**: ServiceContainer resolves appropriate handler
   - RAGHandler for RAG intent
   - ConversationalHandler for chat intent
4. **Execution**: Handler executes domain-specific logic
   - RAG: Hybrid Retrieval → Context Building → LLM Generation
   - Conversational: Direct LLM chat
5. **Response**: Handler returns HandlerResult or streams chunks

### Document Ingestion Flow

1. User upload → MinIO storage
2. Background pipeline: Extract → Clean → Chunk → Embed → Index
3. Store vectors (Qdrant) + metadata (PostgreSQL) + BM25 index

## Infrastructure

### Services (Docker Compose)

- **PostgreSQL 16** + pgvector: Metadata storage
- **Qdrant**: Vector database
- **MinIO**: Object storage for files

### External APIs

- **LLM**: GLM-4.5 (primary), Claude, GPT (fallback)
- **Embedding**: Vietnamese embedding API
- **OCR**: PaddleOCR service (optional)

## Per-User Isolation

Tất cả dữ liệu được scoped by `user_id`:

- BM25 indexes
- Documents và chunks
- Conversations và messages
- API access control

## Migration Notes

### Router → Handler Migration

The system is gradually migrating from router-based to protocol-based architecture:

**Old Pattern** (`src/agents/routers/`):
- Routers handle both classification and execution
- Inherit from `BaseRouter`
- Registered in `RouterRegistry`

**New Pattern** (`src/handlers/`, `src/classification/`):
- Classification separate from execution (SRP)
- Implement `QueryHandler` and `ClassificationStrategy` protocols
- Registered in `ServiceContainer` (DI)

**Backward Compatibility**: `RouterAdapter` in `src/handlers/adapters/` allows old routers to work with new protocol-based system.

See [CLAUDE.md](../CLAUDE.md) for detailed migration guide.
