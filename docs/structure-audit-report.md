# Báo cáo kiểm tra cấu trúc thư mục và chất lượng code

> Ngày: 2026-11-20 · nhánh `develop` · công cụ: `ruff` (qua `uvx`, bộ rule mặc định của dự án và bộ mở rộng), `vulture`, `grep`, `git ls-files`.
> Không sửa code nào. Mọi con số đo trên working tree hiện tại (có thay đổi chưa commit).

## 0. Tóm tắt

| Câu hỏi | Kết luận ngắn |
|---|---|
| Bố cục tổng thể có ổn không? | **Khung chính ổn** (`src/modules/*` theo hexagonal rõ ràng). **Rối ở phần rìa**: thư mục gốc, tooling AI, module không đồng nhất, frontend phân tán. |
| Còn file dư thừa? | **Có.** 2 file không ai import, 1 file placeholder rỗng, ~1.4k dòng monitoring chỉ được re-export, 62 file `.codex/` bị commit, v.v. (mục 3). |
| Tên file đúng PEP 8? | **Gần như hoàn toàn đúng** với module/thư mục Python. 1 file sai (`scripts/test-vlm-page-extraction.py`). 7 tên exception thiếu hậu tố `Error` (mục 4). |
| Có áp dụng chuẩn Python không? | **Một phần.** Rule mặc định của dự án chỉ có `E,F,W,I,B` nên "sạch" (5 lỗi). Khi bật thêm rule chuẩn hiện đại thì có **628** vi phạm. CI format check hiện sẽ **fail** (17 file). mypy tắt 12 loại lỗi. (mục 5). |
| Kiến trúc hexagonal có được giữ? | Chủ yếu có, nhưng có **vi phạm cụ thể** (endpoint chứa nghiệp vụ, domain import adapter) (mục 6). |

Ưu tiên sửa (chi tiết ở mục 8): (1) commit/gitignore tooling, (2) xoá file chết, (3) chạy `ruff format` + `--fix`, (4) tách logic khỏi `chat/api/endpoints.py`, (5) thống nhất tên/chỗ đặt ở frontend, (6) thêm công cụ migration.

---

## 1. Số liệu tổng quan

| Hạng mục | Giá trị |
|---|---|
| File được git theo dõi | 687 |
| `src/` | 335 file (340 file `.py` kể cả chưa track, **38.372 dòng**) |
| `frontend/` | 159 file |
| `tests/` | 64 file |
| `.codex/` | **62 file** (hook JS, agent toml…) |
| `scripts/` | 22 file |
| `docs/` | 15 file |
| `migrations/` | 5 file SQL |
| `.agents/`, `training/`, `.deepeval/` | 5, 4, 1 |

File Python lớn nhất (dấu hiệu "god file"):

| Dòng | File |
|---|---|
| 926 | `src/modules/chat/api/endpoints.py` |
| 884 | `src/shared/infrastructure/llm/client.py` |
| 829 | `src/modules/rag/orchestration/agents/generation_agent.py` |
| 783 | `…/rag/orchestration/state/rag_state.py` |
| 779 | `…/agents/quality_agent.py` |
| 760 | `…/agents/retrieval_agent.py` |
| 718 | `src/tools/retrieval_tools.py` |
| 540 | `src/modules/evaluation/dataset_generation.py` |

---

## 2. Vì sao nhìn vào thấy rối: các vấn đề bố cục

### 2.1 Thư mục gốc lẫn code, tooling AI, tài liệu và rác cục bộ

Có 21 mục ở gốc. Phân loại:

- **Sản phẩm:** `src/`, `frontend/`, `tests/`, `scripts/`, `migrations/`, `docs/`, `Dockerfile`, `docker-compose.yml`, `Makefile`, `pyproject.toml`.
- **Tooling AI (5 thư mục):** `.agents/`, `.claude/` (**1,9 GB**, đã gitignore), `.codex/` (**62 file đang bị track**), `.superpowers/` (916 KB), `.deepeval/`.
- **Tài liệu rải rác:** `README.md`, `quickstart.md` (chưa track), `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` (symlink → `AGENTS.md`), `docs/*.md`, `training/*.md`.
- **Rác/cục bộ:** `logs/` (2,9 MB), `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.venv` (đa số đã ignore nên không phải lỗi, nhưng làm cây thư mục dài).

Vấn đề:
1. `.codex/` có hook, test JS (`__tests__/*.cjs`), agent toml: đây là **cấu hình công cụ cá nhân** nhưng đang nằm trong repo sản phẩm. `.gitignore` ignore `.claude/` và `.agents/` nhưng **không** ignore `.codex/`, `.superpowers/`, `.deepeval/`: không nhất quán.
2. `.agents/skills/*` vẫn nằm trong index (git status báo `D` 5 file) mà `.gitignore` lại ignore `.agents/`. Commit gần nhất ("ignore local .agents tooling directory") mới ignore mà chưa `git rm --cached`.
3. `AGENTS.md` (241 dòng), `CLAUDE.md` (300 dòng) và `docs/code-standards.md` (661 dòng) **trùng nội dung** về quy ước/kiến trúc, dễ lệch nhau.
4. `training/` (4 file hướng dẫn LangGraph/workshop) không liên quan runtime, hợp hơn trong `docs/`.

### 2.2 `docs/` trộn lẫn tài liệu bền và kế hoạch tạm

`docs/superpowers/{plans,specs,implementation-plans}` là kế hoạch/spec sinh ra trong quá trình làm việc với agent (đặt tên theo ngày). Chúng cùng cấp với `system-architecture.md`, `deployment-guide.md`. Nên tách `docs/archive/` hoặc ignore.
Ngoài ra `.gitignore` liệt kê các file docs cụ thể (`docs/deepeval-rag-evaluation.md`, `docs/ingested-chunk-evaluation-workflow.md`, …) để ẩn: dấu hiệu tài liệu bị bỏ lửng.

### 2.3 Module backend không đồng nhất

Quy ước chuẩn là `api / application / domain / infrastructure` (+ `composition.py`). Thực tế:

| Module | Lệch chuẩn thế nào |
|---|---|
| `rag` | Có thêm tầng `orchestration/{agents,graph,state}` (≈3.1k dòng) nằm **ngoài** 4 tầng chuẩn. `infrastructure/` chỉ có `factory.py`. `composition.py` chỉ 1 dòng re-export `factory`. Hai nơi cùng lo lắp ráp. |
| `evaluation` | File rời ở gốc module (`cli.py`, `dataset_generation.py`, `composition.py`) cạnh các thư mục `adapters/ metrics/ reports/ runners/`, tên tầng khác chuẩn. Có thêm `src/server/api/v1/evaluation/` ngoài module. |
| `debug` | Chỉ `api.py`, `schemas.py`, `service.py`, không theo layering. Gắn dưới route `/admin/pipeline-lab` (tên module `debug` ≠ tên route `pipeline-lab`). |
| `admin` | Có `application/`, `infrastructure/` nhưng **không có `__init__.py`**, router lại nằm ở `src/server/api/v1/admin/`. |
| `identity` | Không có `api/` trong module, router nằm ở `src/server/api/v1/auth/`. |
| `classification` | Có `api/` nhưng module gần như dùng nội bộ; `requests.py` có 3 validator sai chữ ký (N805). |

Hệ quả: người đọc không đoán được router của module nằm ở `modules/<m>/api/` hay `server/api/v1/<m>/`. Hiện có **hai nơi** chứa endpoint: `src/modules/{chat,document,legal}/api` và `src/server/api/v1/{auth,admin,evaluation,metrics}`.

### 2.4 Thư mục "ngoài hệ"

- `src/tools/` (2 file, 718 + 251 dòng): registry singleton toàn cục (`init_retrieval_tools()`, `init_ingestion_tools()` gọi trong `lifespan`). Không thuộc module nào, **không có `__init__.py`**, đối lập với luật "tránh global mutable state mới" và "lắp ráp tập trung". Trùng vai trò với `retrieval/application` và `shared/kernel/di`.
- `src/constants/` chỉ có `__init__.py` (enum `HTTPStatus`, `DocumentStatus`…). Chứa enum nghiệp vụ nhưng nằm ngoài `shared/domain`.
- `src/shared/utils/` có 3 file: `agent.py`, `request_trace.py` và **`postprocess.py` rỗng** (docstring "Empty placeholder"). Tên trùng `modules/drafting/application/postprocess.py`.
- `src/shared/infrastructure/persistence/migrations/` chỉ có `__init__.py`, trong khi thư mục `migrations/` thật nằm ở gốc repo: hai nơi cùng tên khái niệm, một nơi rỗng.

### 2.5 Frontend phân tán

- **Hai bộ locale + một thư mục i18n:** `src/locales/{en,vi}`, `src/lib/locales/{en,vi}`, `src/i18n/`. Hai `index.ts` của `en` **khác nhau** (`diff` báo khác). `lib/locales` chỉ được tham chiếu 1 lần. Dễ sửa nhầm bản không dùng.
- `src/i18n/request.ts` **và** `request.tsx` cùng tồn tại (nội dung khác nhau).
- Component "chat" nằm rải ở `components/simple/`, `components/conversation/`, `components/streaming/`, `components/sources/`. Tên `simple` (`SimpleChat`, `simple-client.ts`, `use-simple-chat.ts`) là tàn dư giai đoạn "KIRA Simplified", chẳng mô tả chức năng.
- `frontend/third_party/` chỉ chứa 1 file LICENSE (chưa track).
- Có `frontend/docs/` và `frontend/scripts/` bên cạnh `docs/` và `scripts/` gốc.

---

## 3. File dư thừa / code chết

Đã kiểm chứng bằng `grep` tham chiếu chéo trong `src`, `tests`, `scripts`:

| Mức | File | Bằng chứng | Gợi ý |
|---|---|---|---|
| Chắc chắn chết | `src/shared/infrastructure/auth/csrf.py` | Không file nào import/nhắc | Xoá hoặc nối vào middleware nếu định dùng CSRF (hiện auth dùng JWT cookie, thiếu CSRF là rủi ro bảo mật cần cân nhắc, không chỉ là dead code) |
| Chắc chắn chết | `src/modules/retrieval/infrastructure/vector/dense_retrieval.py` | Không ai tham chiếu | Xoá hoặc dùng; hiện dense search chạy qua `retrieval_adapters.py`/`qdrant_adapter.py` |
| Placeholder | `src/shared/utils/postprocess.py` | 4 dòng, "Empty placeholder" | Xoá |
| Gần như chết | `monitoring/dashboard_config.py` (513 dòng), `agentic_metrics.py` (494), `langsmith_tracing.py` (401) | Chỉ được `monitoring/__init__.py` re-export, không code nào khác dùng | Xác nhận rồi xoá hoặc gắn thật. Riêng `routing_metrics.py` có dùng (`metrics/endpoints.py`) |
| Vulture (100%) | `langsmith_tracing.py:369 exc_tb`, `kernel/base/repository.py:51 entity`, `ports/retrieval.py:215/360/361`, `tools/ingestion_tools.py:23 build_bm25` | Tham số/biến không dùng | Đa số là chữ ký abstract (chấp nhận), kiểm `build_bm25` |
| Tracked không nên | `.codex/**` (62 file), `.deepeval` | Công cụ cá nhân | `git rm -r --cached` + ignore |
| Tracked đã xoá | `.agents/skills/*` (5) | `D` trong `git status` | Commit việc xoá |
| Tên trùng nghĩa | `chat/domain/services/conversation.py` vs `shared/domain/entities/conversation.py` vs handler `conversational.py` | Ba "conversation" | Đổi tên theo vai trò (xem 4.3) |
| Tên trùng | `shared/ports/document_repository.py` vs `retrieval/infrastructure/document_store/document_repository.py` | Port vs implement cùng tên | Chấp nhận được, nhưng nên đặt hậu tố rõ ràng |
| Script khó dùng | `scripts/test-vlm-page-extraction.py` | Tên có `-`, không import được và pytest sẽ nhận nhầm là test | Đổi `vlm_page_extraction_check.py` |
| Script lẻ | `scripts/` 22 file: nhiều `debug_*`, `visualize_*`, `export_report_chapters_docx.py`, `crawl_dut_vanban.py` | Phục vụ báo cáo/ad-hoc, trộn với tooling vận hành | Chia `scripts/{ops,eval,dev}/` hoặc loại bỏ cái không còn dùng |
| In ra stdout | `src/modules/evaluation/cli.py` (14 `print`), `kernel/di/registry.py` (5), `extractor.py` (3) | `T201` | CLI được phép; `registry.py` và `extractor.py` nên dùng logger |

Ghi chú: 19 biến module-level kiểu `_x = None` (singleton toàn cục) trong `src/`, trái với luật "tránh global mutable state mới".

---

## 4. Quy ước đặt tên (PEP 8)

### 4.1 Kết quả

| Đối tượng | Kết quả |
|---|---|
| Thư mục Python trong `src/`, `tests/`, `scripts/` | **100% snake_case** |
| File `.py` trong `src/`, `tests/` | **100% snake_case** |
| `scripts/*.py` | 21/22 đúng; sai: `test-vlm-page-extraction.py` |
| Migration SQL `01-add-...sql` | Dùng dấu gạch nối + số thứ tự, **không phải Python nên không vi phạm PEP 8**, nhưng không theo công cụ chuẩn (xem 6.4) |
| Thư mục thiếu `__init__.py` | `src/tools`, `src/modules/admin` (+`application`, `infrastructure`), `src/modules/evaluation/infrastructure` |

### 4.2 Vi phạm tên trong code (rule `N`)

- **N818** (7): exception thiếu hậu tố `Error`: `InvalidLegalDocumentInput`, `LegalDocumentConflict`, `LegalDocumentNotFound`, `RelationCandidateNotFound`, `InvalidLegalDocumentState`, `LegalProvisionNotFound` (`legal/application/errors.py`), `TimelineConflict` (`legal/domain/errors.py`). Đổi thành `…Error` (`LegalDocumentNotFoundError`…).
- **N805** (3): `classification/api/requests.py` dòng 27, 34, 65, validator Pydantic dùng tham số đầu không phải `self`/`cls` (thiếu `@classmethod` đi kèm `@field_validator`).

### 4.3 Tên mơ hồ hoặc trùng nghĩa

- `chat/domain/services/{conversation.py, rag.py}`, `handlers/{conversational.py, rag_handler.py, drafting_handler.py}`: **không nhất quán hậu tố** (`_handler` có ở hai file, thiếu ở `conversational.py`).
- Đuôi file chung chung lặp lại (`endpoints.py`, `dto.py`, `service.py`, `models.py`, `client.py`, `composition.py`…) là kiểu quen thuộc của modular monolith, **chấp nhận được**, nhưng làm tab IDE khó phân biệt; bật hiển thị đường dẫn hoặc đặt tiền tố module nếu bất tiện.
- `src/modules/legal/…/legal.py` trùng `document/domain/services/chunking/legal.py`.
- Frontend (không thuộc PEP 8 nhưng gây rối): tên file có **3 kiểu**: Pascal 50 · kebab 42 · khác 53. `docs/code-standards.md` quy định "Files: kebab-case" nhưng ví dụ ngay bên dưới lại là `DocumentUpload.tsx` (Pascal): tài liệu tự mâu thuẫn.

---

## 5. Có áp dụng chuẩn Python không?

### 5.1 Cấu hình hiện tại (`pyproject.toml`)

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "B"]
ignore = ["E501", "B008", "E402"]       # E501 line-too-long, E402 import-not-at-top
[tool.mypy]
disable_error_code = [12 mã]            # no-any-return, arg-type, assignment,
                                        # attr-defined, return-value, override,
                                        # union-attr, operator, var-annotated, ...
```

Nhận xét:
- Rule `E,F,W,I,B` chỉ là **tối thiểu**. Không có `N` (pep8-naming), `UP` (pyupgrade), `ANN`, `SIM`, `C4`, `RET`, `PTH`, `T20`, `BLE`, `ARG`, `C901`.
- `E501` bị tắt dù `line-length = 100`: dòng dài không bị phát hiện (formatter vẫn cố gắng).
- mypy tắt **12 loại lỗi**, trong đó `arg-type`, `assignment`, `return-value`, `attr-defined`, `union-attr`: gần như vô hiệu hoá kiểm tra kiểu thực chất. Chạy mypy "xanh" nhưng ít ý nghĩa.
- Không có `.pre-commit-config.yaml`; CI chạy `ruff check`, `ruff format --check`, mypy, pytest.

### 5.2 Kết quả đo

**Rule của dự án** (`ruff check src tests`): **5 lỗi** (4 `I001` sắp xếp import, 1 `F401` import thừa), tự sửa được bằng `--fix`.

**Format** (`ruff format --check`): **17 / 406 file sẽ bị format lại**, trong khi CI có bước `Check Ruff Formatting` → **CI sẽ đỏ** nếu đẩy lên như hiện tại (đa phần là file đang sửa dở, ví dụ `chat/api/endpoints.py`).

**Bộ rule mở rộng** (`N,UP,ANN201,SIM,PTH,T20,ERA,C901,PLR0913,PLR0915,BLE,TRY400,RET,ARG`) trên `src/`: **628 vi phạm**, trong đó 280 tự sửa được.

| Rule | Số | Ý nghĩa | Mức độ |
|---|---|---|---|
| UP045 | 120 | `Optional[X]` thay vì `X \| None` | Dễ, tự động |
| UP006 | 116 | `List/Dict` thay vì `list/dict` | Dễ, tự động |
| **BLE001** | **78** | `except Exception` quá rộng | **Cao**: trái luật "không nuốt exception" |
| PLR0913 | 39 | Hàm quá nhiều tham số | Trung bình |
| ANN201 | 37 | Hàm public thiếu kiểu trả về | Trung bình (luật dự án: public phải có type hint). Thêm 24 lỗi ANN001 (thiếu kiểu tham số) |
| ARG002 / ARG001 | 36 / 18 | Tham số không dùng | Thấp |
| UP035 | 28 | Import typing đã lỗi thời | Dễ |
| T201 | 24 | `print` trong `src/` | Trung bình (14 là CLI) |
| C901 | 20 | Hàm quá phức tạp | **Cao** (liên quan `_stream_generator` ≈ 245 dòng trong `chat/api/endpoints.py`) |
| TRY400 | 20 | `logger.error` thay vì `logger.exception` trong `except` | Trung bình |
| UP042 | 16 | `class X(str, Enum)` → `StrEnum` | Dễ |
| PTH123/108 | 11 | `open()`/`os.unlink` thay vì `pathlib` | Thấp |
| N818 / N805 | 7 / 3 | Tên exception / chữ ký phương thức | Dễ |
| PLR0915 | 7 | Hàm quá nhiều câu lệnh | Cao |
| ERA001 | 3 | Code bị comment | Dễ |

**Logging không thống nhất:** Loguru ở phần lớn `src/` nhưng `worker/*.py` dùng `logging.getLogger(__name__)` (kèm `%s`), còn một số nơi dùng f-string với tag màu (`<blue>[USER REQUEST]</blue>`) → log khó lọc, f-string tính toán kể cả khi level tắt.

**Điểm tốt:** import tuyệt đối `from src...` nhất quán, Python 3.12, docstring đầy đủ ở hầu hết module (rule D100 chỉ báo 1 file), code format cơ bản sạch, `__init__.py` dùng `__all__`, test đặt tên `test_*.py` nhất quán và bám theo tính năng.

---

## 6. Kiến trúc: so với luật của chính dự án

Luật trong `CLAUDE.md`: không logic nghiệp vụ trong endpoint; application/domain không import adapter cụ thể; không query SQLAlchemy trực tiếp ở application/domain; lắp ráp tập trung; hạn chế global state.

### 6.1 Vi phạm đã xác nhận

| # | Vi phạm | Vị trí |
|---|---|---|
| 1 | **Endpoint chứa nghiệp vụ.** `chat/api/endpoints.py` (926 dòng) có `_stream_generator` (~245 dòng), xử lý chunk routing/retrieval/content, `_save_streamed_messages`, `_ensure_conversation_exists`, `_clean_rejection_content`, `_resolve_citation_filenames`, quản lý `AsyncSession` (13 tham số `db`) ngay trong tầng API | `src/modules/chat/api/endpoints.py` |
| 2 | **API nhận `AsyncSession` trực tiếp** (document: 8, legal: 4, auth: 4, admin: 1) thay vì phụ thuộc use case/repository | các `endpoints.py` |
| 3 | **Domain import adapter cụ thể:** `PaddleOCRAdapter` | `document/domain/services/extraction/pdf_progressive.py:66` |
| 4 | **Domain import adapter cụ thể:** `create_embedding_adapter` | `document/domain/services/embedder.py:46` |
| 5 | Domain import hạ tầng chung | `classification/domain/strategies/llm.py` (`src.shared.infrastructure…`) |
| 6 | Global registry ngoài DI | `src/tools/*` + 19 singleton `_x = None` |
| 7 | Import thực hiện lười (`from src.constants…` trong hàm) trong `document_repository.py:432, 485` → dấu hiệu né import vòng | `retrieval/infrastructure/document_store/document_repository.py` |

Điểm tốt: không thấy `sqlalchemy` được import trong `application/` hay `domain/`; ports tách biệt rõ trong `shared/ports/`; có job CI riêng `validate-modular-monolith-architecture.yml` và test `test_refactor_architecture.py`.

### 6.2 `shared/` đang phình

`src/shared/` chứa **cả port, adapter, infrastructure, kernel, domain, utils**. `shared/ports/container.py` (435 dòng) và `shared/kernel/di/container.py` cùng tên "container": hai cơ chế DI song song cần xác định cái nào là chính.
`shared/infrastructure/llm/client.py` (884 dòng) và `shared/adapters/llm/{glm_adapter,traced_adapter}.py` cùng nói chuyện với LLM ở hai tầng khác nhau: ranh giới "client vs adapter" chưa rõ.

### 6.3 Test

64 file test, **phẳng ở `tests/`** (60 file), chỉ `tests/integration/` có 4 file. Test legal chiếm ~30 file, không gom nhóm. Tên chuẩn (`test_*.py`), nhưng không phản chiếu cấu trúc `src/modules/*`. Có `tests/legal_fakes.py` (helper) lẫn với test.

### 6.4 Migration

Schema được tạo từ `models.py` khi khởi động, kèm 5 script SQL đánh số tay ở `migrations/` (`01-…` đến `05-…`), thư mục `persistence/migrations/` rỗng, không có Alembic. Rủi ro: không biết DB đang ở phiên bản nào; môi trường mới có thể thiếu cột (`thinking_data`, cancel support, bảng legal).

---

## 7. Cấu trúc đề xuất

Không cần đập đi làm lại. Đề xuất theo thứ tự chi phí tăng dần:

```text
kira/
├─ src/
│  ├─ modules/<module>/{api,application,domain,infrastructure}/ + composition.py   # giữ
│  ├─ shared/{ports,adapters,infrastructure,kernel,domain}/                       # giữ; bỏ utils/postprocess
│  └─ server/        # chỉ app, middleware, wiring; KHÔNG chứa endpoint của module
├─ frontend/src/
│  ├─ app/  components/<feature>/  lib/{api,hooks,stores,streaming,types}/
│  └─ locales/{en,vi}/              # MỘT nơi duy nhất, xoá lib/locales + i18n trùng
├─ tests/{unit/<module>/, integration/}
├─ scripts/{ops,eval,dev}/
├─ migrations/                      # chuyển sang Alembic (versions/)
├─ docs/{architecture,deployment,evaluation,archive}/
└─ (gốc) README.md, CLAUDE.md (AGENTS.md → symlink), Makefile, pyproject.toml, docker-compose.yml, Dockerfile
```

Quy tắc đặt chỗ router: **mọi router nằm ở `modules/<m>/api/`**, `server/main.py` chỉ `include_router`. Chuyển `server/api/v1/{auth,admin,evaluation,metrics}` về module tương ứng (`identity`, `admin`, `evaluation`, và `metrics` vào `shared/infrastructure/monitoring` hoặc module riêng).

---

## 8. Danh sách việc cần làm (xếp theo ưu tiên)

### P0: làm ngay (rẻ, ít rủi ro)
1. `git rm -r --cached .codex .agents .deepeval` và thêm `.codex/`, `.superpowers/`, `.deepeval/` vào `.gitignore` (hoặc quyết định giữ có chủ đích).
2. `uvx ruff check src tests --fix` rồi `uvx ruff format src tests` để CI không đỏ.
3. Xoá: `shared/utils/postprocess.py`, `csrf.py`, `dense_retrieval.py` (sau khi xác nhận không dùng; **riêng CSRF xem lại nhu cầu bảo mật** vì auth bằng cookie).
4. Đổi tên `scripts/test-vlm-page-extraction.py` → `vlm_page_extraction_check.py`.
5. Thêm `__init__.py` còn thiếu (`src/tools`, `modules/admin/**`, `evaluation/infrastructure`).
6. Frontend: chọn một thư mục locale, xoá bản trùng; hợp nhất `i18n/request.ts|tsx`.

### P1: chuẩn hoá Python
7. Bật thêm rule vào `pyproject.toml`, theo giai đoạn: `UP`, `N`, `RET`, `SIM`, `T20`, `TRY400`, sau đó `ANN` (chỉ cho code public) và `BLE001`. Dùng `--fix` cho nhóm UP (≈280 lỗi tự sửa).
8. Đổi 7 tên exception thành `…Error`; sửa 3 validator ở `classification/api/requests.py`.
9. Thu hẹp danh sách `disable_error_code` của mypy dần (bắt đầu bằng `attr-defined`, `union-attr`).
10. Thống nhất logger: Loguru cho cả worker; bỏ f-string có tag màu trong log.
11. Thêm `pre-commit` (ruff + ruff-format) để lỗi không đến được CI.

### P2: kiến trúc
12. Tách `chat/api/endpoints.py`: chuyển `_stream_generator`, lưu message, xử lý chunk vào `chat/application/streaming.py` / `ChatSessionService`; endpoint chỉ còn parse request và trả `StreamingResponse` (< 150 dòng).
13. API không nhận `AsyncSession`; inject use case đã gắn repository.
14. `document/domain/services/{embedder,extraction/pdf_progressive}.py`: nhận `EmbeddingPort`/`OCRPort` qua constructor; để `composition.py` lo wiring.
15. Quyết định số phận `src/tools/*` và `monitoring/{dashboard_config,agentic_metrics,langsmith_tracing}`: gắn vào DI hoặc xoá.
16. Đưa `rag/orchestration` về layout chuẩn hoặc ghi rõ trong tài liệu đó là tầng ngoại lệ; dọn `rag/composition.py` ↔ `infrastructure/factory.py`.
17. Chuyển router của `identity/admin/evaluation` về `modules/*/api/`.

### P3: tổ chức
18. Gom `tests/` theo module; tách `scripts/` thành `ops/eval/dev`.
19. Dùng **Alembic**, bỏ `migrations/*.sql` rải rác.
20. Dồn `AGENTS.md`/`CLAUDE.md`/`docs/code-standards.md` về một nguồn; chuyển `training/` và `docs/superpowers/` sang `docs/archive/`.
21. Frontend: đặt lại tên `simple/` (→ `chat/`), thống nhất quy ước tên file (PascalCase cho component, kebab-case cho phần còn lại, sửa `code-standards.md` cho khớp).

---

## 9. Giới hạn của báo cáo

- `ruff`/`vulture` chạy qua `uvx` trên working tree đang có thay đổi dở; số liệu format/lint có thể đổi sau khi commit.
- "File chết" được xác định bằng tham chiếu văn bản (`grep`): import động qua chuỗi (`importlib`, entry point trong config) có thể bị bỏ sót. Kiểm tra lại trước khi xoá.
- Chưa chạy `pytest`, `mypy`, `npm run lint` và chưa dựng dịch vụ nào; không đánh giá độ phủ test hay lỗi runtime.
- Chưa đọc từng dòng của toàn bộ 38k dòng; các nhận xét kiến trúc dựa trên cấu trúc, kích thước file, import và đọc mẫu các file chính (`main.py`, `chat/application/*`, `langgraph_pipeline.py`, `document_tasks.py`).
