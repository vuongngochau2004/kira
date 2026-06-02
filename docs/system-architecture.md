# Kiến trúc Hệ thống

## Tổng quan Architecture

K.I.R.A Simplified theo **4-layer architecture pattern** với tách biệt rõ ràng giữa các lớp:

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

### 1. Multi-Agent Routing

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

### 2. Hybrid Retrieval (RRF)

- **Dense**: Vector similarity search via Qdrant
- **BM25**: Keyword search per-user index
- **RRF**: Reciprocal Rank Fusion for result merging

### 3. Intelligent OCR Fallback

- PyMuPDF native text extraction
- Low-quality detection → PaddleOCR fallback
- 2D layout sorting for reading order

## Luồng dữ liệu

### Query Processing Flow
1. User query → FastAPI `/chat/stream`
2. Orchestrator: Quick Filter → LLM Classification → Router Dispatch
3. RAGRouter: Hybrid Retrieval (Dense + BM25)
4. Context Building + LLM Generation
5. SSE Streaming response

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
