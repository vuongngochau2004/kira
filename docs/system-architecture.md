# Kiến trúc Hệ thống (System Architecture)

Tài liệu này cung cấp thiết kế kiến trúc toàn diện của **KIRA (Knowledge-based Intelligent Retrieval Assistant)** — nền tảng RAG hiệu năng cao tối ưu cho tiếng Việt, được xây dựng theo mô hình **Hexagonal Modular Monolith** ở backend và **Next.js 16 App Router** ở frontend.

---

## 1. Tổng quan Kiến trúc Toàn hệ thống (System Overview)

Hệ thống tuân thủ nghiêm ngặt nguyên tắc phụ thuộc hướng tâm của Hexagonal Architecture (Ports & Adapters), chia tách rõ ràng các tầng trách nhiệm:

```mermaid
---
config:
  theme: default
  look: classic
---
flowchart TB
    subgraph Clients["🖥️ Client Layer (Frontend)"]
        WebUI["Web Application<br/>(Next.js 16 • React 19 • Tailwind v4)"]
        ZustandStore["Client Stores<br/>(Zustand • TanStack Query)"]
        SSEClient["Streaming Client<br/>(EventSource / fetch-sse)"]
        WebUI --> ZustandStore --> SSEClient
    end

    subgraph Serving["🌐 Serving Layer (src/server/)"]
        FastAPI["FastAPI Application Core"]
        AuthMiddleware["JWT Authentication Middleware"]
        SSEHandler["SSE Streaming Protocol Handler"]
        
        subgraph Endpoints["API Endpoints (/api/v1/)"]
            EP_Auth["/auth (JWT Login/Register)"]
            EP_Doc["/documents (Upload/Manage)"]
            EP_Chat["/chat (Streaming Chat)"]
            EP_Legal["/legal (Knowledge Graph QA)"]
            EP_Eval["/evaluation (DeepEval Benchmark)"]
            EP_Health["/health (Service Health & Probes)"]
        end
    end

    subgraph Modules["📦 Application Core Modules (src/modules/)"]
        ChatMod["Chat Module<br/>• Session & History<br/>• SSE Event Orchestration"]
        ClassMod["Classification Module<br/>• Intent Routing<br/>• Multi-Strategy Classifier"]
        RAGMod["RAG Module (LangGraph)<br/>• Multi-Agent Workflow<br/>• Citation Verification"]
        RetMod["Retrieval Module<br/>• Dense + BM25<br/>• RRF Fusion + TEI Rerank"]
        LegalMod["Legal Module<br/>• Neo4j Knowledge Graph<br/>• Temporal Validity Reasoning"]
        DocMod["Document Module<br/>• Processing Lifecycle<br/>• Chunk & Audit State"]
        EvalMod["Evaluation Module<br/>• DeepEval Test Runner<br/>• Metrics Reporting"]
    end

    subgraph Background["⚡ Background Ingestion (Celery & Redis)"]
        CeleryWorker["Celery Worker Tasks<br/>• documents.process<br/>• legal.index_graph"]
        DoclingExtractor["Docling / PyMuPDF<br/>Layout Analysis & OCR"]
        VLMVerifier["VLM Verification<br/>Page Quality Gate"]
    end

    subgraph Shared["🔌 Shared Kernel & Ports (src/shared/)"]
        Ports["Domain Ports (Interfaces)<br/>• LLMClientPort • VectorStorePort<br/>• EmbeddingPort • RerankerPort<br/>• StoragePort • LegalGraphPort"]
        Adapters["Infrastructure Adapters<br/>• QdrantAdapter • MinIOAdapter<br/>• Neo4jAdapter • TEIAdapter<br/>• OpenAI / GLM / Gemini / Ollama"]
        Infra["Persistence & Security<br/>• SQLAlchemy Async Session<br/>• Password Cryptography"]
    end

    subgraph Persistence["💾 Storage & Vector Infrastructure"]
        PG[("PostgreSQL 16 + pgvector<br/>Metadata, Chat History, Chunks")]
        QdrantDB[("Qdrant Vector DB<br/>1024-dim Dense Collection")]
        Neo4jDB[("Neo4j 5 Graph DB<br/>Legal Hierarchy & Cross-Refs")]
        MinIODB[("MinIO S3 Storage<br/>Raw Documents & Page Audits")]
        RedisDB[("Redis 7<br/>Task Queue & Response Caching")]
    end

    subgraph ExternalServices["🤖 External AI & Embedding APIs"]
        LLMProviders["LLM Providers<br/>(OpenAI-compatible • GLM • Gemini • Ollama)"]
        TEIEmbedding["TEI Embedding API<br/>(BAAI/bge-m3 1024-dim)"]
        TEIReranker["TEI Reranker API<br/>(bge-reranker-v2-m3)"]
    end

    %% Client to Serving
    SSEClient <--> SSEHandler
    WebUI --> Endpoints
    Endpoints --> AuthMiddleware --> FastAPI

    %% Serving to Modules
    FastAPI --> ChatMod & DocMod & LegalMod & EvalMod
    ChatMod --> ClassMod --> RAGMod
    RAGMod --> RetMod & LegalMod
    RAGMod --> LLModPorts["Ports.LLM"] --> Adapters
    DocMod -. Enqueue Job .-> RedisDB --> CeleryWorker
    CeleryWorker --> DoclingExtractor --> VLMVerifier

    %% Modules to Ports & Adapters
    Modules --> Ports
    Ports --> Adapters
    Adapters --> Infra

    %% Worker & Adapters to Storage
    CeleryWorker --> MinIODB & PG & QdrantDB
    Adapters --> PG & QdrantDB & Neo4jDB & MinIODB & RedisDB
    Adapters --> LLMProviders & TEIEmbedding & TEIReranker
```

---

## 2. Mô hình Hexagonal Architecture (Ports & Adapters)

KIRA áp dụng nguyên lý cô lập hoàn toàn nghiệp vụ cốt lõi (**Inside**) khỏi chi tiết hạ tầng kỹ thuật (**Outside**):

```mermaid
---
config:
  theme: neutral
---
flowchart LR
    subgraph OutsideLeft["Hạ tầng Đầu vào (Driving Adapters)"]
        HTTPClient["Web Browser / Client"]
        FastAPIRouter["FastAPI Endpoints"]
        CeleryTrigger["Celery Task Triggers"]
    end

    subgraph InsideCore["Lõi Ứng Dụng (Hexagon Core - Inside)"]
        subgraph UseCases["Application Services (Use Cases)"]
            ChatUC["ChatUseCase / StreamChat"]
            DocUC["UploadDocument / ProcessDocument"]
            LegalUC["LegalQAUseCase / TraverseGraph"]
            EvalUC["RunEvaluationUseCase"]
        end

        subgraph DomainModel["Domain Model & Rules"]
            DomainEntities["Entities: Document, Chunk, Citation, User"]
            DomainServices["IntentClassifier, RRFEngine, ChunkingStrategy"]
            DomainPorts["Ports (Abstract Interfaces):<br/>• LLMClientPort<br/>• VectorStorePort<br/>• EmbeddingPort<br/>• DocumentStoragePort<br/>• LegalGraphPort"]
        end
    end

    subgraph OutsideRight["Hạ tầng Đầu ra (Driven Adapters)"]
        QdrantAdapter["QdrantVectorAdapter"]
        PostgresRepo["PostgreSQL Repositories"]
        MinIOAdapter["MinIOStorageAdapter"]
        Neo4jAdapter["Neo4jGraphAdapter"]
        TEIAdapter["TEIClient (Embed/Rerank)"]
        LLMAdapters["LLM Clients (OpenAI / GLM / Gemini)"]
    end

    HTTPClient --> FastAPIRouter --> ChatUC & DocUC & LegalUC & EvalUC
    CeleryTrigger --> DocUC
    ChatUC & DocUC & LegalUC & EvalUC --> DomainServices --> DomainPorts
    
    DomainPorts --> QdrantAdapter --> Qdrant[(Qdrant DB)]
    DomainPorts --> PostgresRepo --> PG[(Postgres DB)]
    DomainPorts --> MinIOAdapter --> MinIO[(MinIO S3)]
    DomainPorts --> Neo4jAdapter --> Neo4j[(Neo4j DB)]
    DomainPorts --> TEIAdapter --> TEIAPI["TEI Microservice"]
    DomainPorts --> LLMAdapters --> CloudLLM["External LLM APIs"]
```

### Quy tắc Phụ thuộc Bắt buộc (Dependency Rule):
1. **Mã nguồn tầng `application/` và `domain/`** chỉ được phụ thuộc vào `Ports` (Interfaces trừu tượng), không bao giờ import trực tiếp các `Adapters` cụ thể từ `infrastructure/`.
2. **Không có Business Logic trong FastAPI Router**: Router chỉ kiểm tra HTTP DTO, ủy quyền xử lý cho Application Service, và trả về Response/SSE Stream.
3. **Mọi câu truy vấn dữ liệu** (PostgreSQL, Qdrant, MinIO) đều bắt buộc lọc theo `user_id` để đảm bảo an toàn đa người dùng (Multi-Tenancy).

---

## 3. Luồng Xử lý Dữ liệu Chi tiết (Data Flows)

### 3.1 Luồng Hội thoại Thời gian thực (Real-time SSE Streaming Chat)

```mermaid
---
config:
  theme: default
---
sequenceDiagram
    autonumber
    actor User as Người dùng (Web UI)
    participant API as FastAPI Router (/api/v1/chat/stream)
    participant Auth as JWT Middleware
    participant ChatApp as Chat Application Service
    participant Classifier as Intent Classifier (Composite)
    participant LangGraph as LangGraph RAG Agent
    participant Retrieval as Hybrid Retrieval Engine
    participant TEI as TEI / Embedding API
    participant Qdrant as Qdrant Vector DB
    participant Postgres as PostgreSQL DB
    participant LLM as Active LLM Provider

    User->>API: POST /api/v1/chat/stream {message, conversation_id}
    API->>Auth: Xác thực JWT token từ cookie
    Auth-->>API: User Context (user_id)
    API->>ChatApp: execute_stream(message, user_id, conversation_id)
    
    ChatApp->>Postgres: Tải lịch sử hội thoại (Conversation & Messages)
    Postgres-->>ChatApp: Lịch sử tin nhắn gần nhất
    
    ChatApp->>Classifier: classify_intent(query, history)
    Note over Classifier: Chuỗi kiểm tra: Keyword -> Cache -> LLM Fast Path
    Classifier-->>ChatApp: Intent: RAG | Conversational | LegalQA
    
    ChatApp-->>User: SSE Event: 'routing' {intent, confidence}

    alt Intent == RAG / LegalQA
        ChatApp->>LangGraph: run_graph(query, user_id, intent)
        LangGraph->>Retrieval: hybrid_search(query, user_id, top_k=20)
        
        par Truy vấn Song song
            Retrieval->>TEI: embed_query(query) -> 1024-dim Vector
            TEI-->>Retrieval: Dense Vector
            Retrieval->>Qdrant: Search vectors (payload: user_id)
            Qdrant-->>Retrieval: Dense Chunks Top-K
        and
            Retrieval->>Postgres: BM25 PyVi Keyword Search (user_id)
            Postgres-->>Retrieval: Sparse Chunks Top-K
        end

        Retrieval->>Retrieval: Reciprocal Rank Fusion (RRF k=60)
        Retrieval->>TEI: rerank(query, candidates, top_n=5)
        TEI-->>Retrieval: Reranked Chunks + Relevance Scores
        Retrieval-->>LangGraph: Retrieved Chunks & Citations

        ChatApp-->>User: SSE Event: 'retrieval' {chunks_found, citations_preview}
        
        LangGraph->>LLM: Stream prompt with grounded context
        loop Token Streaming
            LLM-->>ChatApp: Text Token Delta
            ChatApp-->>User: SSE Event: 'token' {delta}
        end

        LangGraph->>LangGraph: Verify citation grounding score
        ChatApp-->>User: SSE Event: 'citation' {verified_citations}
    else Intent == Conversational
        ChatApp->>LLM: Direct Chat Stream (History + Query)
        loop Token Streaming
            LLM-->>ChatApp: Text Token Delta
            ChatApp-->>User: SSE Event: 'token' {delta}
        end
    end

    ChatApp->>Postgres: Lưu User Message & Assistant Message (kèm citations)
    ChatApp-->>User: SSE Event: 'done' {message_id, finish_reason}
```

---

### 3.2 Luồng Nhập liệu Tài liệu Bất đồng bộ (Asynchronous Document Ingestion)

```mermaid
---
config:
  theme: default
---
flowchart TD
    Start([Người dùng Upload File PDF / DOCX / TXT]) --> UploadAPI["POST /api/v1/documents/upload"]
    
    subgraph FastPath["Xử lý Tức thời (API Response)"]
        UploadAPI --> ValidateFile{"Kiểm tra Dung lượng & MIME"}
        ValidateFile -->|Không hợp lệ| Return400["Trả mã lỗi 400 Bad Request"]
        ValidateFile -->|Hợp lệ| SaveMinIO["Lưu file gốc vào MinIO S3<br/>(Bucket: kira-documents)"]
        SaveMinIO --> InsertDB["Tạo Document Record trong PostgreSQL<br/>(status = 'pending')"]
        InsertDB --> EnqueueCelery["Đẩy Task 'documents.process' vào Redis Queue"]
        EnqueueCelery --> Return202["Trả về 202 Accepted {document_id, status: 'pending'}"]
    end

    subgraph WorkerPath["Xử lý Nền (Celery Document Worker)"]
        EnqueueCelery -.-> WorkerPick["Worker nhận Task từ Redis"]
        WorkerPick --> UpdateProcessing["Cập nhật status = 'processing'"]
        
        UpdateProcessing --> ExtractBranch{"Loại File & Cấu hình"}
        ExtractBranch -->|PDF| PDFStrategy["Docling Parser (Ưu tiên Layout & Bảng)"]
        ExtractBranch -->|DOCX / PPTX / TXT| NativeExtract["python-docx / python-pptx / text parser"]
        
        PDFStrategy --> CheckDocling{"Docling thành công?"}
        CheckDocling -->|Có| MarkdownText["Chuẩn hoá Markdown Text"]
        CheckDocling -->|Lỗi / Font Hỏng| FallbackOCR["PyMuPDF Render 300DPI + PaddleOCR"]
        FallbackOCR --> MarkdownText
        NativeExtract --> MarkdownText

        MarkdownText --> QualityGate{"Kiểm tra Chất lượng Text<br/>(Độ dài, Ngôn ngữ tiếng Việt)"}
        QualityGate -->|Thất bại| MarkReview["Cập nhật status = 'failed' / 'needs_review'"]
        
        QualityGate -->|Đạt chuẩn| LegalChunking["Phân đoạn Văn bản (Chunking)<br/>• Recursive Character / Legal Hierarchy<br/>• Size: 2048, Overlap: 256"]
        
        LegalChunking --> GenEmbed["Tạo Embedding qua TEI BGE-M3<br/>(Batch 16 chunks, 1024-dim)"]
        
        GenEmbed --> UpsertQdrant["Upsert Chunks & Vectors vào Qdrant<br/>Payload: {user_id, doc_id, text, page}"]
        UpsertQdrant --> UpdateBM25["Cập nhật chỉ mục từ khoá BM25 (PyVi)"]
        UpdateBM25 --> MarkCompleted["Cập nhật status = 'completed', chunks_count, finished_at"]
    end

    Return202 --> ClientPoll["Client Poll hoặc SSE Thông báo Ingest Hoàn tất"]
    MarkCompleted -.-> ClientPoll
```

---

### 3.3 Máy Trạng thái RAG LangGraph (LangGraph State Machine)

```mermaid
---
config:
  theme: default
---
stateDiagram-v2
    [*] --> ClassifyIntent : Nhận User Prompt

    state ClassifyIntent {
        [*] --> CheckKeyword
        CheckKeyword --> CheckCache : No Match
        CheckCache --> LLMClassify : Cache Miss
    }

    ClassifyIntent --> DirectResponse : Intent == Conversational
    ClassifyIntent --> QueryExpansion : Intent == RAG | LegalQA

    DirectResponse --> StreamOutput : Sinh câu trả lời trực tiếp

    state QueryExpansion {
        [*] --> RewriteQuery : Mở rộng từ đồng nghĩa & pháp lý
        RewriteQuery --> [*]
    }

    QueryExpansion --> ParallelRetrieval
    
    state ParallelRetrieval {
        [*] --> DenseSearch : Qdrant Vector Search
        [*] --> SparseSearch : BM25 PyVi Search
        [*] --> GraphSearch : Neo4j Entity Traverse
        DenseSearch --> MergeRRF
        SparseSearch --> MergeRRF
        GraphSearch --> MergeRRF
        MergeRRF --> TEIRerank : Cross-Encoder Rerank
        TEIRerank --> [*]
    }

    ParallelRetrieval --> ContextGrading : Top Chunks

    state ContextGrading {
        [*] --> EvaluateRelevance : Kiểm tra điểm liên quan
    }

    ContextGrading --> ReRetrieve : Điểm liên quan < Ngưỡng (Attempt < 2)
    ReRetrieve --> ParallelRetrieval : Mở rộng truy vấn
    ContextGrading --> SynthesizeAnswer : Điểm liên quan >= Ngưỡng

    state SynthesizeAnswer {
        [*] --> GenerateResponse : LLM sinh câu trả lời kèm citation tags [1], [2]
    }

    SynthesizeAnswer --> CitationGroundingCheck

    state CitationGroundingCheck {
        [*] --> VerifyOverlap : Đối soát text chunk và câu trả lời
    }

    CitationGroundingCheck --> RegenerateAnswer : Grounding Score < 0.7
    RegenerateAnswer --> SynthesizeAnswer
    CitationGroundingCheck --> StreamOutput : Grounding Score >= 0.7

    state StreamOutput {
        [*] --> EmitTokens : Bắn SSE Events ra Frontend
    }

    StreamOutput --> SaveState
    SaveState --> [*] : Hoàn tất chu trình
```

---

## 4. Mô hình Thực thể Dữ liệu (Entity Relationship Diagram)

Sơ đồ quan hệ cơ sở dữ liệu lưu trữ quan hệ trong PostgreSQL 16:

```mermaid
---
config:
  theme: neutral
---
erDiagram
    USERS ||--o{ DOCUMENTS : "owns"
    USERS ||--o{ CONVERSATIONS : "starts"
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : "contains"
    DOCUMENTS ||--o{ DOCUMENT_AUDIT_LOGS : "logs"
    CONVERSATIONS ||--o{ MESSAGES : "has"
    MESSAGES ||--o{ CITATIONS : "references"
    DOCUMENT_CHUNKS ||--o{ CITATIONS : "sourced_from"
    
    USERS {
        uuid id PK
        string email UK
        string hashed_password
        string full_name
        string role
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    DOCUMENTS {
        uuid id PK
        uuid user_id FK
        string filename
        string original_filename
        string file_type
        integer file_size
        string s3_key
        string status "pending | processing | completed | failed"
        integer chunks_count
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }

    DOCUMENT_CHUNKS {
        uuid id PK
        uuid document_id FK
        uuid user_id FK
        integer chunk_index
        text content
        text clean_content
        integer page_number
        integer token_count
        string qdrant_point_id
        jsonb metadata
        timestamp created_at
    }

    CONVERSATIONS {
        uuid id PK
        uuid user_id FK
        string title
        boolean is_pinned
        timestamp deleted_at "Soft Delete"
        timestamp created_at
        timestamp updated_at
    }

    MESSAGES {
        uuid id PK
        uuid conversation_id FK
        uuid user_id FK
        string role "user | assistant | system"
        text content
        string intent_type
        jsonb reasoning_steps
        timestamp created_at
    }

    CITATIONS {
        uuid id PK
        uuid message_id FK
        uuid chunk_id FK
        integer citation_index
        text snippet
        float relevance_score
        float grounding_score
        timestamp created_at
    }

    DOCUMENT_AUDIT_LOGS {
        uuid id PK
        uuid document_id FK
        string extraction_method "docling | vlm | paddleocr"
        float quality_score
        jsonb details
        timestamp created_at
    }
```

---

## 5. Cấu trúc Module & Giới hạn Trách nhiệm (Modular Monolith Boundaries)

Hệ thống được tổ chức dạng thư mục rõ ràng theo cấu trúc phân tầng Hexagonal:

```text
src/
├── server/                           # Serving Layer - Điểm giao tiếp HTTP duy nhất
│   ├── main.py                      # Khởi tạo FastAPI, Lifespan và Global Handlers
│   ├── middleware/                  # JWT auth, CORS, logging context
│   └── api/v1/                      # Định nghĩa Router endpoints
│       ├── auth/                    # Đăng nhập, đăng ký, refresh token
│       ├── chat/                    # SSE streaming chat và quản lý hội thoại
│       ├── documents/               # Upload, quản lý và inspect chunks tài liệu
│       ├── legal/                   # Truy vấn đồ thị kiến thức pháp luật Neo4j
│       └── evaluation/              # Chạy benchmark đánh giá RAG DeepEval
│
├── modules/                          # Application Core Modules - Nghiệp vụ thuần tuý
│   ├── chat/                        # Quản lý phiên chat, định dạng SSE stream
│   ├── classification/              # Chiến lược phân loại ý định (Keyword, LLM, LRU Cache)
│   ├── document/                    # Upload pipeline, logic chunking và kiểm soát status
│   ├── drafting/                    # Tác vụ tự động soạn thảo văn bản
│   ├── evaluation/                  # Bộ service DeepEval, tính metric Faithfulness/Recall
│   ├── identity/ & auth/            # Quản lý thực thể User, mật khẩu, JWT credentials
│   ├── legal/                       # Xử lý đồ thị pháp lý, quan hệ văn bản, hiệu lực thời gian
│   ├── rag/                         # Multi-agent LangGraph workflow, context grading
│   └── retrieval/                   # Dense vector, BM25 tiếng Việt, RRF, Cross-encoder Reranker
│
├── shared/                           # Shared Kernel - Thành phần dùng chung toàn hệ thống
│   ├── ports/                       # Interfaces trừu tượng (LLM, VectorStore, Embedding, Storage...)
│   ├── adapters/                    # Concrete Adapters (Qdrant, MinIO, Neo4j, TEI, GLM, Gemini...)
│   ├── infrastructure/              # Hạ tầng kỹ thuật (Database connection pool, Auth, Celery)
│   ├── domain/                      # Shared entities, Value Objects và Exceptions
│   └── kernel/                      # Dependency Injection container và Service Registry
│
├── config/                           # Cấu hình hệ thống
│   ├── config.py                    # Pydantic Settings đọc từ file .env
│   └── settings.yaml                # Cấu hình tĩnh (retrieval k, chunk sizes, thresholds)
│
└── worker/                           # Celery background workers
    ├── celery_app.py                # Khởi tạo Celery Application
    ├── document_tasks.py            # Background task xử lý file và sinh vector
    └── legal_tasks.py               # Background task phân tích đồ thị quan hệ pháp luật
```

---

## 6. Chiến lược Cô lập Đa Người dùng (Multi-Tenancy Isolation)

Để ngăn ngừa triệt để rủi ro rò rỉ dữ liệu chéo người dùng:

1. **Vector Store (Qdrant)**:
   - Mọi vector khi nạp vào collection đều đính kèm trường `user_id` trong payload.
   - Khi truy vấn `client.search()`, hệ thống luôn luôn inject filter bắt buộc:
     ```python
     Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=current_user_id))])
     ```
2. **Từ khoá (BM25 Sparse Index)**:
   - Mỗi người dùng sở hữu không gian chỉ mục BM25 độc lập theo `user_id`.
3. **Cơ sở dữ liệu Quan hệ (PostgreSQL)**:
   - Các bảng `DOCUMENTS`, `DOCUMENT_CHUNKS`, `CONVERSATIONS`, `MESSAGES` đều có foreign key `user_id`.
   - Các Repository luôn áp đặt điều kiện `WHERE user_id = :user_id` trong tất cả các câu lệnh `SELECT`, `UPDATE`, `DELETE`.
4. **Đối tượng Lưu trữ (MinIO S3)**:
   - Khóa lưu trữ đối tượng phân cấp theo `documents/{user_id}/{document_id}/{filename}`.

---

## 7. Môi trường Thực thi & Cấu hình Cổng (Network Topology)

```mermaid
---
config:
  theme: default
---
flowchart LR
    Browser["🌐 Web Browser (User)"]
    
    subgraph HostPorts["Host Port Mappings"]
        Port3001["Port 3001<br/>Next.js Web UI"]
        Port8006["Port 8006<br/>FastAPI Backend Server"]
        Port5435["Port 5435<br/>PostgreSQL 16 (pgvector)"]
        Port6333["Port 6333 / 6334<br/>Qdrant HTTP / gRPC"]
        Port9000["Port 9000 / 9001<br/>MinIO API / Console"]
        Port6379["Port 6379<br/>Redis Queue & Cache"]
        Port7474["Port 7474 / 7687<br/>Neo4j Browser / Bolt"]
    end

    Browser -->|HTTP| Port3001
    Browser -->|REST / SSE| Port8006
    Port3001 -->|Internal Proxy| Port8006

    Port8006 --> Port5435 & Port6333 & Port9000 & Port6379 & Port7474
```

---

*Tài liệu kiến trúc KIRA được cập nhật và kiểm thử đồng bộ với Mermaid.js v11 standards.*
