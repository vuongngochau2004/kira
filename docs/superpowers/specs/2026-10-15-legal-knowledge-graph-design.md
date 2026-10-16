# Vietnamese Legal Knowledge Graph — Design Spec

- Date: 2026-10-15
- Status: Draft (awaiting review)
- Scope: Sub-projects 1–4 combined into one design: legal corpus ingestion (admin upload),
  Neo4j legal knowledge graph, point-in-time graph-aware retrieval, legal citations in chat/UI.

## 1. Goal

Let KIRA users ask questions about Vietnamese law — in particular the legal documents taking
effect from 2026-07-01 — and receive answers that:

1. Are grounded only in published legal text, cited down to Article/Clause/Point and document
   number (e.g. "Điều 12 Khoản 3, Luật Đất đai số 31/2024/QH15").
2. Are correct **at a point in time**: the answer uses the provision version in force on the
   date the question refers to (default: today), and can compare two dates.
3. Follow links between new and old documents (amends, replaces, repeals, guides, based on),
   stored in a Neo4j graph.

### Success criteria

- For a golden dataset of 50–100 legal questions, answers cite the provision version that is in
  force at the resolved date (temporal correctness) and the exact document number and
  Article/Clause (citation exactness).
- No provision version is ever served outside its validity interval.
- Every legal relation used in answering has an approved review record with source evidence.

## 2. Decisions

| # | Topic | Decision |
|---|---|---|
| 1 | Corpus scope | One shared, system-wide legal corpus. Private user documents remain `user_id`-isolated and are out of scope for this feature. |
| 2 | Ingestion | Admin uploads files with a metadata form now. A vbpl.vn crawler is a later sub-project reusing the same pipeline. |
| 3 | Relations | Rules + LLM propose candidate relations with evidence; an admin reviews them; only approved relations reach the graph. |
| 4 | Time model | Full point-in-time: versioned content per provision with `valid_from` / `valid_to`. |
| 5 | Query date | Detected automatically from the question only (rules, LLM fallback). Default today. No UI date picker. |
| 6 | Storage | Neo4j holds the approved legal graph and versions; Qdrant (+ BM25) indexes provision versions for search; PostgreSQL holds ingestion and review state. |

Data source note: thuvienphapluat.vn is a commercial site with terms of use and paywalled
content and is not used as an automated source. Admins upload documents obtained from official
sources (vbpl.vn, congbao.chinhphu.vn).

## 3. Graph Schema (Neo4j)

### Nodes

**`LegalDocument`**
- `doc_id` (UUID, matches PostgreSQL `legal_documents.id`)
- `number` (e.g. `45/2024/QH15`, unique)
- `doc_type` (`law`, `decree`, `circular`, `decision`, `resolution`, `other`)
- `title`, `issuer`, `issued_date`, `effective_date`
- `source_url`, `file_key` (MinIO object key), `sha256`

**`Provision`** — a structural unit; holds no text.
- `provision_key` (unique, stable), format `<number>#D<article>[.K<clause>[.<point>]]`,
  e.g. `45/2024/QH15#D12.K3.a`
- `level` (`article` | `clause` | `point`)
- `label` ("Điều 12", "Khoản 3", "Điểm a"), `heading`, `chapter_label`

**`ProvisionVersion`** — the text of a provision during one interval.
- `version_id` (UUID), `text`, `text_hash`, `page`
- `valid_from` (date, inclusive), `valid_to` (date, exclusive; `null` = open-ended)

### Relationships

| Type | From → To | Meaning |
|---|---|---|
| `HAS_PART` | Document→Provision, Provision→Provision | Structure Article → Clause → Point |
| `HAS_VERSION` | Provision → ProvisionVersion | Content versions |
| `INTRODUCED_BY` | ProvisionVersion → Provision | The amending provision that produced this version |
| `AMENDS` | Provision → Provision | Amendment/supplement of a target provision |
| `REPEALS` | Provision → Provision, Document → Document | Repeal |
| `REPLACES` | Document → Document | Full replacement |
| `GUIDES` | Document/Provision → Document/Provision | Implementation guidance |
| `BASED_ON` | Document → Document | Legal basis ("Căn cứ") |

Every legal relationship (`AMENDS`, `REPEALS`, `REPLACES`, `GUIDES`, `BASED_ON`) carries
`effective_date`, `evidence_text`, `evidence_page`, `review_id`, `approved_by`, `approved_at`.

### Validity rules

- A version is in force on date `D` iff `valid_from <= D` and (`valid_to` is null or
  `D < valid_to`).
- Invariant: versions of one provision never overlap; on any date at most one version is in
  force.
- The base version of each provision has `valid_from = LegalDocument.effective_date`, unless the
  document states a different effective date for that provision (partial effectiveness), which
  the parser/metadata records per provision.
- An approved `AMENDS` with effective date `E` ends the version in force at `E`
  (`valid_to = E`) and starts a new version (`valid_from = E`) with the amended text, linked by
  `INTRODUCED_BY`.
- An approved `REPEALS` (provision level) or `REPLACES` (document level, applied to every
  provision of the target) with effective date `E` ends the version in force at `E` and
  creates no successor.

### Constraints and indexes

- Unique: `LegalDocument.number`, `Provision.provision_key`, `ProvisionVersion.version_id`.
- Indexes: `ProvisionVersion.valid_from`, `ProvisionVersion.valid_to`.

### Search index mirror

Each `ProvisionVersion` maps to exactly one Qdrant point in collection `legal_provisions`
(`point_id = version_id`). Payload: `provision_key`, `number`, `doc_type`, `label`,
`valid_from`, `valid_to` (open-ended stored as `9999-12-31` so range filters work), `page`.
The legal BM25 index stores the same keys.

## 4. Ingestion and Review Pipeline

### PostgreSQL staging tables

**`legal_documents`**
- `id`, metadata fields (`number`, `doc_type`, `title`, `issuer`, `issued_date`,
  `effective_date`, `source_url`), `file_key`, `sha256`
- `parsed_structure` (JSONB tree of provisions with `provision_key`, text, page, optional
  per-provision effective date)
- `status`: `uploaded → parsing → in_review → publishing → published`, or `failed`
- `error_detail`, `uploaded_by`, timestamps

**`legal_relation_candidates`**
- `id`, `legal_document_id` (source document)
- `type`, `source_provision_key` (nullable for document-level)
- `target_number`, `target_provision_ref` (e.g. `D12.K3`), `effective_date`
- `new_text` (required for `AMENDS`)
- `evidence_text`, `evidence_page`
- `extractor` (`rule` | `llm`), `confidence` (0–1)
- `status`: `pending | approved | rejected | unresolved_target`
- `reviewed_by`, `reviewed_at`, `review_note`
- `flags` (e.g. `llm_extraction_incomplete`)

Schema change is delivered as `migrations/03-legal-tables.sql` plus SQLAlchemy models in
`src/shared/infrastructure/persistence/database/models.py`.

### Flow

1. **Upload** — `POST /api/v1/legal/documents` (admin only, `UserRole.admin`), multipart file +
   metadata. Store file in MinIO, insert `legal_documents` row, enqueue `legal.process`.
   Duplicate `number` or `sha256` is rejected with 409.
2. **Parse structure** — reuse extractors from the `document` module for text; a legal parser
   (extending `src/modules/document/domain/services/chunking/legal.py` patterns) builds the
   Article → Clause → Point tree and `provision_key`s. Pure rules, fixture-tested.
3. **Extract relations**
   - Rules: document-number regex (`\d+/\d{4}/[A-ZĐ0-9-]+`) and phrase patterns for
     "Căn cứ", "thay thế", "bãi bỏ", "hướng dẫn", "sửa đổi, bổ sung".
   - LLM (via the existing LLM port, JSON-schema output): amendment blocks such as
     "Điều X được sửa đổi, bổ sung như sau: …" → target provision + new text.
4. **Resolve targets** — look up `target_number` in `legal_documents` (published or not).
   Missing target → `unresolved_target`. When a document is uploaded, re-resolve all
   `unresolved_target` candidates whose `target_number` equals its number.
5. **Auto-approval** — only `BASED_ON` at document level with exact number match to a known
   document. `AMENDS`, `REPEALS`, `REPLACES`, `GUIDES` always require admin review. The
   auto-approved type list is configurable in `settings.yaml` (`legal.auto_approve_types`).
6. **Review** — admin sees evidence next to the proposal and approves, rejects, or edits
   (target, effective date, new text). Document moves to `in_review` after extraction.
7. **Publish** — admin triggers `POST /api/v1/legal/documents/{id}/publish`; enqueue
   `legal.publish`. Publishing is allowed while candidates are still `pending` or
   `unresolved_target`; those candidates are simply not applied until approved, and approving
   one later triggers a re-publish of the affected provisions.

### Publish: rebuild, never patch

For the document being published:
1. Upsert `LegalDocument`, `Provision`s, `HAS_PART`.
2. Collect affected provision keys: the document's own provisions plus every target of its
   approved relations.
3. For each affected provision, call the pure `timeline.build(base_version, approved_changes)`
   using **all** approved changes targeting it (from any document), sorted by effective date,
   and replace its version chain in Neo4j.
4. Apply document-level relations (`REPLACES`, `GUIDES`, `BASED_ON`, document `REPEALS`).
5. Sync the search index: upsert points for the new chain, delete points of that provision whose
   `version_id` is no longer in the chain; same for BM25.
6. Set `status = published`.

Properties: out-of-order uploads yield the correct timeline; rejecting a previously approved
relation is handled by re-running the rebuild for its target; a failed publish is safely
retryable because all writes are keyed by `provision_key` / `version_id`.

`version_id` is derived deterministically (UUIDv5 of `provision_key` + `valid_from` +
`text_hash`) so a rebuild that produces the same version reuses the same id and point.

### Admin UI

`frontend/src/app/admin/legal/`: document list by status, document detail with parsed
structure, relation review screen (evidence on the left, proposal on the right, approve /
reject / edit), publish button. Uses `frontend/src/components/ui/`.

### Admin API (`/api/v1/legal`, admin only unless noted)

- `POST /documents` — upload
- `GET /documents`, `GET /documents/{id}` — list/detail
- `GET /documents/{id}/candidates` — relation candidates
- `PATCH /candidates/{id}` — approve / reject / edit
- `POST /documents/{id}/publish` — publish
- `GET /provisions/{provision_key}?date=YYYY-MM-DD` — any authenticated user; version in force
  plus history, used by citation links

## 5. Retrieval and Point-in-Time Answering

### Routing

Add intent `legal_qa` to the `classification` module: keyword fast path (`luật`, `nghị định`,
`thông tư`, `quy định`, `hiệu lực`, document-number regex) plus LLM fallback. A new
`LegalQAHandler` (subclass of `QueryHandlerBase`) is registered with the existing handlers and
queries the shared legal corpus only.

### Step 1 — Temporal resolution (`TemporalResolver`)

- Rules first: explicit dates (`1/7/2026`), years ("năm 2025" → 2025-12-31, or today if the
  year is the current year), "hiện nay"/"hiện hành" → today, "trước/sau ngày X".
- LLM fallback for relative references such as "trước khi Luật Đất đai 2024 có hiệu lực";
  output `{mode: "single" | "compare", dates: [...], reason}`. Referenced documents are resolved
  to dates via `LegalGraphPort.get_effective_date(number)`. "Trước ngày X" resolves to X − 1 day.
- No temporal reference → `mode = single`, `date = today`.

### Step 2 — Date-filtered search

- Dense: Qdrant `legal_provisions` with filter `valid_from <= D` and `valid_to > D`.
- BM25: legal index, same validity filter applied.
- RRF fusion (reuse `src/modules/retrieval/domain/services/fusion.py`) → `legal.seed_top_k`
  (default 20) seed provisions.
- In `compare` mode, run the search once per date and union the seeds.

### Step 3 — Graph expansion (`LegalGraphPort.expand_context`)

Bounded Cypher per seed (`legal.max_depth`, `legal.max_guides`):
- Parent article / sibling clauses for context.
- `GUIDES` provisions in force at `D`, capped at `max_guides`, re-scored by embedding similarity
  to the question.
- Amendment provenance: the provision and document that introduced the version.
- `amended_after` flag: the provision has a version with `valid_from > D`.
- `compare` mode: the versions in force at D1 and D2 for each seed provision.

### Step 4 — Rerank and context assembly

Reuse the existing reranking service. Each context block has a standard header:
`[Điều 12 Khoản 3 — Luật Đất đai số 31/2024/QH15 — hiệu lực 01/08/2024 → nay]`.

### Step 5 — Generation

A legal prompt in `src/modules/legal/domain/prompts/` requiring:
- answers grounded only in context, each claim cited to Article/Clause + document number;
- first sentence states the applied date ("Áp dụng tại ngày …");
- an explicit notice when `amended_after` is set;
- in `compare` mode, before/after content plus the document that caused the change;
- an explicit "not found" answer when context is insufficient.

The existing citation verification step is reused.

### SSE compatibility

Citation payloads gain one optional field; existing fields are unchanged:

```json
"legal": {
  "number": "31/2024/QH15",
  "doc_type": "law",
  "provision_key": "31/2024/QH15#D12.K3",
  "label": "Điều 12 Khoản 3",
  "valid_from": "2024-08-01",
  "valid_to": null,
  "amended_after": false
}
```

The frontend citation component shows a validity badge, the `amended_after` warning, and links to
`GET /api/v1/legal/provisions/{provision_key}`.

## 6. Components and Architecture Placement

### Shared port and adapter

- `src/shared/ports/legal_graph.py` — `LegalGraphPort` (ABC):
  `upsert_document_structure`, `replace_provision_timeline`, `apply_document_relation`,
  `get_versions_at`, `expand_context`, `get_effective_date`, `health_check`; DTOs
  `LegalProvisionRef`, `ProvisionVersionDTO`, `GraphExpansion`.
- `src/shared/adapters/graph/neo4j_adapter.py` — async official `neo4j` driver; Cypher kept as
  named constants in `src/shared/adapters/graph/cypher.py`; creates constraints/indexes at
  startup.
- Vector search reuses `QdrantAdapter` with collection `legal_provisions`; add range-filter
  support if the adapter lacks it.

### Module `src/modules/legal/`

```text
legal/
  api/             endpoints.py, schemas.py
  application/     ingest_document.py, extract_relations.py, review_relation.py,
                   publish_document.py, legal_qa.py
  domain/          parser/        (Article→Clause→Point tree, provision_key)
                   extraction/    (regex rules, LLM prompt + output schema)
                   temporal/      (TemporalResolver)
                   timeline.py    (pure version-chain builder, no I/O)
                   prompts/       (legal QA, compare)
  infrastructure/  repositories.py (SQLAlchemy: legal_documents, relation_candidates)
                   legal_index.py  (Qdrant + BM25 sync for the legal corpus)
  composition.py   wiring of Neo4jAdapter, QdrantAdapter, LLM client, repositories
```

- `timeline.py` is the core: input base version + approved changes, output non-overlapping
  versions or `TimelineConflict`.
- Endpoints contain no business logic; application code uses ports and repositories only.
- Router mounted in `src/server/main.py` at `/api/v1/legal`.

### Worker

`src/worker/legal_tasks.py`: `legal.process`, `legal.publish` on the existing Celery app.

### Infrastructure and configuration

- `docker-compose.yml`: service `neo4j` (`neo4j:5-community`, ports 7474/7687, volume
  `neo4j_data`, healthcheck).
- `src/config/config.py` / `.env.example`: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`,
  `LEGAL_ENABLED` (default `false`).
- `src/config/settings.yaml`, block `legal:` — `qdrant_collection: legal_provisions`,
  `seed_top_k: 20`, `max_depth: 2`, `max_guides: 5`, `auto_approve_types: [BASED_ON]`.
- `pyproject.toml`: add `neo4j` (the only new dependency).

### Startup

When `LEGAL_ENABLED=true`, lifespan initializes the Neo4j driver, runs `health_check`, ensures
constraints and the `legal_provisions` collection, and closes the driver on shutdown. If Neo4j
is unavailable, the error is logged and `legal_qa` is disabled (chat replies that legal lookup
is temporarily unavailable); the backend keeps running.

### Frontend

- `frontend/src/app/admin/legal/` — admin screens (section 4).
- Citation component — validity badge and `amended_after` warning.
- `frontend/src/lib/api/simple-client.ts` — legal API client and types.

## 7. Error Handling

| Situation | Handling |
|---|---|
| Structure parsing finds no articles | `status = failed`, `error_detail` set; admin re-uploads or fixes metadata |
| LLM extraction timeout / invalid JSON | Bounded retry; keep rule-based candidates; flag `llm_extraction_incomplete` |
| Target document not in corpus | `unresolved_target`; auto re-resolve when the target is uploaded |
| Two approved changes hit one provision on the same effective date | `TimelineConflict`; publish stops for that document with `failed` and the conflicting candidate ids; admin resolves |
| Neo4j/Qdrant write fails mid-publish | `status = failed`; retry is idempotent |
| Neo4j unavailable during chat | `legal_qa` disabled with a user-facing notice; other chat flows unaffected |
| Graph expansion fails mid-answer | Answer from seed provisions, note that related documents could not be checked |
| No provision in force at `D` | Answer that no provision in force on `D` was found; no speculation |

All errors are logged with `doc_id`, `provision_key`, `candidate_id` as applicable; API responses
return safe messages.

## 8. Testing

- **Pure unit tests (highest priority)**
  - `timeline.py`: multiple amendments, out-of-order changes, repeal, replace, withdrawal of an
    approved change, partial effectiveness, conflicts; property tests for "no overlap" and
    "at most one version in force on any date".
  - Parser: fixtures from real Laws, Decrees, Circulars (Article/Clause/Point, appendices,
    repealed articles).
  - Extraction regexes: each phrase pattern and document-number variant.
  - `TemporalResolver`: "hiện nay", "năm 2025", "trước 1/7/2026", compare questions, no date.
- **Application tests** with a fake `LegalGraphPort` and fake vector store: ingest → review →
  publish; `legal_qa` date filtering, expansion, compare mode, `amended_after`.
- **Integration tests** (`@pytest.mark.integration`) against Neo4j from docker-compose: Cypher,
  constraints, publish idempotency.
- **SSE contract test**: existing citation fields unchanged, `legal` optional.
- **Frontend**: validity badge component and review screen.

## 9. Evaluation

DeepEval golden dataset of 50–100 legal questions covering: current law, past dates, before/after
2026-07-01 comparisons, questions needing guiding documents, and unanswerable questions.
Metrics: existing faithfulness and contextual precision/recall, plus:
- **Temporal correctness** — cited version is the one in force at the resolved date.
- **Citation exactness** — cited document number and Article/Clause match the golden answer.

## 10. Out of Scope

- vbpl.vn crawler (next sub-project).
- Analyzing private user documents against new law.
- UI date picker.
- End-user graph visualization.
