# Đề xuất tái cấu trúc KIRA

> 2026-11-21. Bản đề xuất, chưa thực hiện. Đọc cùng [structure-audit-report.md](structure-audit-report.md) và [architecture-and-flows.md](architecture-and-flows.md).

Mục tiêu (theo yêu cầu): **đọc là biết sửa ở đâu, sửa thì sửa ít chỗ, logic nghiệp vụ dễ thấy, dùng chung đúng chỗ, không over-engineering, test có cấu trúc rõ.**

---

## 1. Hexagonal có tốt cho KIRA không?

**Ý tưởng thì tốt, cách áp dụng hiện tại thì không.**

Ý tưởng cốt lõi của hexagonal: logic nghiệp vụ không phụ thuộc trực tiếp vào DB/LLM/Qdrant, nên đổi nhà cung cấp hay viết test không cần hạ tầng. Ý tưởng này **nên giữ**.

Cái làm KIRA rối là **nghi thức** (ceremony) bị áp dụng đồng loạt cho mọi thứ, kể cả chỗ không cần. Số đo thực tế:

| Dấu hiệu | Số đo trong `src/` | Hệ quả |
|---|---|---|
| 4 tầng cố định × 11 module | `api` 14 file · `application` 39 · `domain` 57 · `infrastructure` 25; **110 file `__init__.py`** | Một tính năng nhỏ trải qua 4–5 thư mục |
| Port (interface) chỉ có 1 cài đặt | **17 port có đúng 1 implementation**, 3 port có **0** (`KeywordSearchPort`, `RAGWorkflowPort`, `RetrievalDocumentPort`) | Interface không mang lại gì, chỉ thêm một bước nhảy khi đọc code |
| Port thật sự cần (≥2 cài đặt) | Chỉ `LLMPort` (3), `EmbeddingPort` (4), `ClassificationStrategyBase` (6), `QueryHandlerBase` (5), `OCRPort`/`StoragePort`/`VectorStorePort` (2) | Đây là chỗ duy nhất interface đáng tồn tại |
| Hai hệ DI song song | `shared/ports/container.py` (435 dòng, `ScopeManagerBase`, `ServiceDescriptor`…) **và** `shared/kernel/di/{container,registry}.py`, cộng 9 file `composition.py`, cộng singleton toàn cục trong `src/tools/` | Không rõ đối tượng được tạo ở đâu |
| Một khái niệm, nhiều lớp | Thao tác "xoá tài liệu" có `DeleteDocumentRequest` (api) + `DeleteDocumentRequest` (dto) + `DeleteDocument` (use case) + `DocumentDeleteResult` (dto) + `DocumentDeleteResponse` (api). `DocumentStatus` khai báo **2 lần**, `Citation` **3 lần** (`Citation` ×2, `RAGCitation`) | Thêm một field phải sửa 4–5 class |
| Đặt sai chỗ vì tuân thủ hình thức | Repository của **document** nằm trong `retrieval/infrastructure/document_store/` | Tìm code theo tên tính năng không ra |

Ví dụ luồng **upload** hiện tại đi qua **9 file**:
`document/api/endpoints.py` → `api/requests.py` → `application/dto.py` → `application/upload.py` → `shared/ports/document_repository.py` + `shared/ports/storage.py` → `retrieval/infrastructure/document_store/document_repository.py` + `shared/adapters/storage/minio_adapter.py` → wiring ở `document/composition.py` → `api/responses.py`.

Với một dự án ~38k dòng, 1–2 người phát triển, chạy một tiến trình (monolith), mức này là **over-engineering**: tốn công đọc và sửa, mà lợi ích (thay adapter, test cô lập) chỉ cần ở vài chỗ.

---

## 2. Các repo tham khảo: tổ chức thế nào, học được gì

Đã xem trực tiếp cây thư mục trên GitHub (2026-11-21):

| Repo | Ngôn ngữ | Cách tổ chức | Lấy gì cho KIRA |
|---|---|---|---|
| **open-webui** | Python/FastAPI | Rất phẳng: `routers/<feature>.py`, `models/<feature>.py` (ORM + truy vấn), `retrieval/{loaders,vector/dbs/<provider>.py,web}`, `utils/`, `config.py`, `main.py` | **Sự đơn giản**: mỗi tính năng một router + một file data. Pattern **`vector/dbs/` + `factory.py`**: interface chỉ xuất hiện khi có nhiều provider |
| **onyx** | Python/FastAPI + Celery | Gói theo **năng lực**: `chat/`, `llm/`, `document_index/`, `connectors/`, `indexing/`, `background/celery/`; HTTP tách riêng ở `server/<feature>/`; truy vấn DB gom ở `db/<entity>.py` (hàm thuần); test `tests/unit/onyx/<cùng đường dẫn>` + `tests/integration/` | **Gần KIRA nhất** (RAG + Celery + Postgres). Lấy: gói theo tính năng, `interfaces.py` + `factory.py` cho LLM/document index, **test phản chiếu cây mã nguồn** |
| **anything-llm** | Node.js | `server/{endpoints,models,utils,jobs}`; `utils/{AiProviders,EmbeddingEngines,EmbeddingRerankers,vectorDbProviders}/<provider>/`; `__tests__/{endpoints,models,utils}` | Gom **mọi provider ngoài vào một chỗ**, mỗi provider một thư mục, test chia theo nhóm |
| **FastGPT** | TypeScript monorepo | `packages/service/core/{ai,app,chat,dataset,workflow}`, `common/`, `support/` | Gom theo nghiệp vụ (`dataset`, `chat`), tách phần dùng chung (`common`). Ngôn ngữ khác nên chỉ tham khảo ý tưởng |
| **ragflow** | Đang chuyển phần lớn sang **Go** (`internal/`, `cmd/`) | Rất nhiều thư mục (`dao/ service/ handler/ router/ rag/ deepdoc/ agent/ …`) | **Không chọn làm mẫu**: đang dời sang ngôn ngữ khác và phân mảnh hơn cả KIRA |

**Lựa chọn:** lấy **khung của onyx** (gói theo tính năng, test phản chiếu cây mã nguồn, Celery tách riêng), **độ phẳng của open-webui** (ít tầng, router mỏng), và **pattern provider của open-webui/anything-llm** (interface + factory chỉ ở nơi có nhiều nhà cung cấp).

---

## 3. Có nên đập đi xây lại không?

**Không viết lại từ đầu.** Nên **tái cấu trúc tại chỗ, di chuyển code theo từng tính năng** (dùng `git mv` để giữ lịch sử), test luôn xanh sau mỗi bước.

Lý do:
- Phần giá trị nhất của KIRA nằm ở **logic nghiệp vụ**: parser điều khoản pháp luật, temporal/timeline, trích xuất PDF nhiều tầng, BM25 tiếng Việt, hybrid search, quality gate. Phần này đúng và có test. Viết lại là tự tạo bug.
- Thứ cần "đập" là **lớp keo**: port 1 cài đặt, DTO trùng, use-case class bọc một hàm, 2 hệ DI, `composition.py`, `src/tools`. Phần này xoá được mà không đổi hành vi.

Nói cách khác: **giữ ruột, thay vỏ**.

---

## 4. Cấu trúc đích

### 4.1 Toàn repo

```text
kira/
├── backend/                 # toàn bộ Python (giống onyx, open-webui)
│   ├── kira/                # package chính (thay cho "src")
│   ├── tests/
│   ├── scripts/
│   ├── alembic.ini
│   └── pyproject.toml
├── frontend/
├── deploy/                  # Dockerfile(s), docker-compose.yml, cloudflared
├── docs/
├── Makefile
├── README.md
└── CLAUDE.md                # AGENTS.md, GEMINI.md → symlink
```

Gốc repo chỉ còn ~8 mục. Tooling AI (`.codex`, `.superpowers`, …) ra khỏi git.

> Đổi `src` → `kira` là tuỳ chọn. Lý do nên đổi: `src` không phải tên package (import `src.modules...` lạ, dễ đụng tên). Vì bước di chuyển module đằng nào cũng đổi toàn bộ import, nên đổi luôn một lần là rẻ nhất.

### 4.2 Backend

```text
backend/kira/
├── main.py                  # tạo FastAPI app, include_router — không gì khác
├── config.py                # Settings (pydantic) + settings.yaml
├── deps.py                  # MỌI hàm tạo dependency dùng chung (get_db, get_llm, get_current_user...)
├── worker.py                # celery_app + đăng ký task
│
├── core/                    # kỹ thuật dùng chung, không có nghiệp vụ
│   ├── logging.py  errors.py  health.py  tracing.py
│
├── db/
│   ├── session.py           # engine, async session
│   ├── models.py            # TOÀN BỘ ORM (hoặc tách models/<entity>.py khi > 600 dòng)
│   └── migrations/          # Alembic
│
├── providers/               # NƠI DUY NHẤT có interface + factory
│   ├── llm/        base.py  factory.py  openai_compatible.py  glm.py  gemini.py  ollama.py
│   ├── embedding/  base.py  factory.py  tei.py  ollama.py  api.py
│   ├── rerank/     base.py  factory.py  tei.py  llm.py  scoring.py
│   ├── ocr/        base.py  paddle.py  docling.py
│   ├── storage.py           # MinIO (1 cài đặt → không cần base)
│   ├── vector_store.py      # Qdrant
│   └── graph_store.py       # Neo4j
│
├── auth/                    # identity + auth
│   ├── router.py  service.py  repository.py  schemas.py  security.py (jwt, cookie, csrf, rate limit)
│
├── documents/
│   ├── router.py            # upload, list, get, download, delete, cancel, chunks
│   ├── service.py           # nghiệp vụ: lưu MinIO, tạo row, enqueue, xoá, huỷ
│   ├── repository.py        # mọi SQL của documents/chunks
│   ├── schemas.py
│   ├── tasks.py             # celery: documents.process, delete job
│   └── processing/          # pipeline xử lý (giữ nguyên ruột hiện tại)
│       ├── pipeline.py  clean.py  chunk.py  quality.py  embed.py
│       └── extract/  pdf.py (progressive) pdf_docling.py pdf_vlm.py pdf_pymupdf.py docx.py pptx.py image.py text.py
│
├── retrieval/               # dùng chung cho chat và legal
│   ├── search.py            # hybrid_search(): API duy nhất mà module khác gọi
│   ├── dense.py  bm25.py  fusion.py
│
├── chat/
│   ├── router.py            # /chat/stream, /completions, /conversations
│   ├── service.py           # load/tạo conversation → route → handler → lưu message
│   ├── repository.py        # conversations, messages, search
│   ├── schemas.py
│   ├── sse.py               # HỢP ĐỒNG SSE: mọi event được tạo ở đây (khớp frontend lib/streaming)
│   ├── intent.py            # classifier: keyword → cache → llm
│   ├── citations.py
│   ├── handlers/            # conversational.py  rag.py  drafting.py
│   └── rag/                 # LangGraph: graph.py  state.py  nodes/{plan,retrieve,generate,check}.py  prompts.py
│
├── drafting/                # docx renderer + template văn bản hành chính (handler nằm ở chat/handlers)
│
├── legal/                   # giữ nhiều ruột nhất (nghiệp vụ phức tạp thật)
│   ├── router.py  service.py  repository.py  schemas.py  tasks.py
│   ├── parser/  extraction/  temporal/  scrapers/
│   ├── graph.py             # truy vấn Neo4j (cypher)
│   ├── search.py            # tìm điều khoản theo ngày hiệu lực
│   └── qa.py                # handler LEGAL_QA cho chat
│
├── evaluation/              # router.py  runner.py  metrics.py  datasets.py  cli.py
└── admin/                   # router.py (overview, metrics, pipeline-lab)  service.py
```

Mỗi tính năng có **cùng bộ 4 file**: `router.py` · `service.py` · `repository.py` · `schemas.py` (+ `tasks.py` nếu có Celery). Mở thư mục nào cũng biết file nào làm gì.

### 4.3 Test: phản chiếu cây mã nguồn

```text
backend/tests/
├── conftest.py              # fixture chung: fake LLM/embedding/storage, db session
├── fakes.py                 # Fake providers (thay cho port 1-cài-đặt)
├── unit/                    # không cần Docker, chạy < 30 s
│   ├── documents/  test_service.py  processing/test_chunk.py  processing/test_extract_pdf.py ...
│   ├── retrieval/  test_bm25.py  test_fusion.py  test_search.py
│   ├── chat/       test_service.py  test_sse.py  test_intent.py  rag/test_graph.py ...
│   ├── legal/      parser/  temporal/  test_service.py  test_search.py ...
│   └── providers/  test_embedding_tei.py  test_rerank_tei.py ...
└── integration/             # cần Postgres/Qdrant/Neo4j/MinIO (marker integration)
    ├── documents/  legal/  ...
```

Quy tắc: **`kira/X/Y.py` → `tests/unit/X/test_Y.py`.** Muốn biết test của file nào, đổi đường dẫn là ra. Tên test theo đơn vị (`test_chunk.py`), không theo câu chuyện (`test_bm25_index_rebuilds_when_worker_adds_or_removes_documents.py` → thành một hàm test trong `tests/unit/retrieval/test_bm25.py`).

Ánh xạ 64 file test hiện tại theo tiền tố:

| Hiện tại | Chuyển về |
|---|---|
| `test_legal_*` (~33 file) | `unit/legal/…` (parser, temporal, extraction, search, publish…) + `integration/legal/` |
| `test_document_*`, `test_soft_delete_*`, `test_security_upload_*` | `unit/documents/` |
| `test_bm25_*`, `test_hybrid_search_*`, `test_retrieval_agent_reranking` | `unit/retrieval/` |
| `test_rag_*`, `test_generation_*`, `test_quality_agent_*`, `test_chat_*`, `test_conversation_search` | `unit/chat/` và `unit/chat/rag/` |
| `test_tei_*`, `test_embedding_factory`, `test_llm_client_*` | `unit/providers/` |
| `test_evaluation_*` | `unit/evaluation/` |
| `test_startup_health`, `test_logging_intercept` | `unit/core/` |
| `test_refactor_architecture`, `test_application_services` | Viết lại theo luật mới (mục 5) hoặc bỏ |

### 4.4 Frontend: theo tính năng

```text
frontend/src/
├── app/                     # chỉ route (page.tsx, layout.tsx), mỏng
├── features/
│   ├── chat/        components/  hooks/  api.ts  sse.ts (parser, đối xứng với backend chat/sse.py)
│   ├── documents/   components/  hooks/  api.ts
│   ├── legal/       components/  hooks/  api.ts
│   ├── admin/       components/  api.ts
│   └── auth/
├── components/ui/           # dùng chung thật sự (button, dialog...)
├── lib/                     # http client, utils, store dùng chung
└── locales/{en,vi}/         # MỘT nơi
```

Gộp `components/{simple,conversation,streaming,sources}` → `features/chat/components/`. Test vẫn đặt cạnh file (`X.test.tsx`) như hiện tại.

---

## 5. Bộ luật (ngắn, để giữ được lâu)

1. **Một tính năng = một thư mục.** Tìm theo tên nghiệp vụ là thấy.
2. **`router.py` mỏng:** parse request → gọi `service` → trả response. Không SQL, không vòng lặp nghiệp vụ. Mục tiêu dưới 200 dòng.
3. **`service.py` chứa nghiệp vụ.** Dùng hàm thường hoặc một class; nhận `db` và client cần thiết qua tham số. Không có class `XxxUseCase` chỉ để bọc một hàm `execute()`.
4. **`repository.py` chứa mọi SQL của tính năng.** Chỉ `service` gọi nó.
5. **`schemas.py`: một bộ Pydantic** dùng cho cả API và service. Chỉ tách model riêng khi hình dạng thật sự khác nhau.
6. **Interface chỉ ở `providers/`, và chỉ khi có từ 2 cài đặt thật.** Còn lại import class cụ thể. Test dùng `fakes.py` hoặc `monkeypatch`.
7. **Không DI container.** Dependency đi qua FastAPI `Depends` và các hàm `get_x()` có cache, đặt ở `deps.py`. Đọc `deps.py` là biết mọi thứ được tạo ở đâu.
8. **Hướng import:** `router → service → repository / providers / retrieval / core / db`. Các tính năng gọi nhau **chỉ qua `service.py` hoặc `search.py` công khai** (ví dụ `chat` gọi `retrieval.search.hybrid_search`), không import ruột của nhau.
9. **Giới hạn kích thước:** file trên 400 dòng hoặc hàm trên 60 dòng thì tách. Ruff `C901` và `PLR0915` sẽ nhắc.
10. **Test phản chiếu đường dẫn** (mục 4.3).

Check kiến trúc trong CI (`validate-modular-monolith-architecture.yml`) viết lại theo đúng các luật 2, 4, 6, 8. Đơn giản hơn luật hiện tại.

---

## 6. Sau tái cấu trúc: muốn sửa X thì sửa ở đâu

| Muốn sửa | File cần chạm |
|---|---|
| Thêm/đổi event SSE | `chat/sse.py` + `frontend/features/chat/sse.ts` |
| Đổi prompt RAG | `chat/rag/prompts.py` |
| Đổi logic chọn intent | `chat/intent.py` |
| Thêm nhà cung cấp LLM | `providers/llm/<new>.py` + một dòng trong `factory.py` |
| Đổi cách chunk | `documents/processing/chunk.py` |
| Thêm cột cho document | `db/models.py` + 1 migration Alembic + `documents/schemas.py` |
| Đổi trọng số hybrid search | `retrieval/search.py` (hoặc `settings.yaml`) |
| Thêm API tài liệu | `documents/router.py` + `service.py` (+ `repository.py` nếu có SQL) |
| Upload: toàn bộ luồng | `documents/router.py` → `service.py` → `repository.py` + `providers/storage.py` (**4 file thay vì 9**) |

---

## 7. Lộ trình thực hiện

Mỗi giai đoạn là **một nhánh / một PR**, kết thúc khi `pytest` + `ruff` + frontend test đều xanh. Không đổi hành vi, không đổi API/SSE trong lúc di chuyển.

| # | Việc | Rủi ro |
|---|---|---|
| 0 | Commit WIP hiện tại; dọn P0 trong báo cáo kiểm tra (gitignore tooling, ruff fix/format, xoá file chết). Ghi lại baseline test. | Thấp |
| 1 | Tạo `providers/` bằng cách gom `shared/adapters/*` + `shared/infrastructure/llm/client.py` + reranker; xoá port 1-cài-đặt và port không dùng; thêm `tests/fakes.py`. | Trung bình |
| 2 | Tạo `deps.py`; thay `kernel/di`, `ports/container.py`, các `composition.py`, `src/tools` bằng `get_x()`. | Trung bình |
| 3 | Di chuyển theo tính năng, mỗi tính năng một PR, theo thứ tự **auth → documents → retrieval → chat (+classification, rag, drafting) → legal → evaluation → admin/debug**. Mỗi PR: gộp `api/application/domain/infrastructure` → `router/service/repository/schemas`, gộp DTO trùng, chuyển test sang `tests/unit/<feature>/`. | Trung bình–cao ở bước chat (SSE); có test SSE ở cả hai phía làm lưới an toàn |
| 4 | Alembic: tạo baseline từ schema hiện tại, bỏ `migrations/*.sql` tay. | Trung bình (kiểm tra trên DB dev trước) |
| 5 | `src` → `backend/kira` (sed import), cập nhật Dockerfile, Makefile, CI, `CLAUDE.md`, README. | Thấp (cơ học) |
| 6 | Frontend → `features/`, một thư mục locale. | Thấp–trung bình |
| 7 | Bật thêm rule ruff (`UP, N, SIM, RET, BLE, C901, ANN` cho code public), siết mypy dần. | Thấp |

Kết quả ước tính (sẽ đo lại sau khi làm): file `__init__.py` từ 110 còn khoảng 30; bỏ 9 `composition.py` và 2 hệ DI; số port/interface từ khoảng 30 class còn khoảng 6 base class trong `providers/`; mỗi luồng chính đi qua 4–5 file thay vì 8–10.

---

## 8. Những gì cố ý KHÔNG làm

- Không thêm framework DI, không thêm event bus, không tách microservice.
- Không tạo interface "phòng khi sau này cần". Khi có cài đặt thứ hai thì mới tạo.
- Không tách `domain/` riêng cho từng tính năng. Nghiệp vụ phức tạp thật (legal parser/temporal, document processing, rag graph) đã có thư mục con theo nội dung của nó.
- Không đổi API, SSE, schema DB trong lúc di chuyển code. Đổi hành vi là PR riêng.
