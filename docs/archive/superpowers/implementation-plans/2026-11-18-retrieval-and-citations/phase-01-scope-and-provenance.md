# Phase 01 — Tenant scope and chunk provenance

## Context links

- [Parent plan](plan.md); [Plan 2 query contract](../2026-11-18-agent-core-and-routing/plan.md)
- [Search use case](../../../../src/modules/retrieval/application/search_use_case.py); [Qdrant adapter](../../../../src/modules/retrieval/infrastructure/vector/qdrant_store.py)
- [BM25 manager](../../../../src/modules/retrieval/infrastructure/keyword/bm25_manager.py); [RRF fusion](../../../../src/modules/retrieval/domain/services/fusion.py)

## Overview

- Date: 2026-11-18; priority: P1; implementation: pending; review: pending; dependency: Plan 2 standalone-query contract.

## Key insights

The live personal-RAG call supplies a user ID, but public personal search APIs and Qdrant helpers accept `None`. Fusion currently keys chunks by document ID plus chunk index; missing IDs can collapse unrelated results into the same key. BM25 is per-user but process-local and rebuilds from stored chunks, so restart and deletion behavior deserve explicit checks.

## Requirements

1. Personal search must reject a missing user ID at the application boundary; shared legal search remains explicit and separate.
2. Every candidate must carry `user_id`, `document_id`, `chunk_index` or stable `chunk_id`, score origin, and source filename/page when available.
3. Discard malformed or unowned candidates before fusion, reranking, generation, and citation enrichment.
4. Deletion and ingestion updates must invalidate or rebuild the correct user's BM25 index; another user's index must remain untouched.
5. External filename lookup must also be owner-scoped before returning document titles.

## Architecture

Create a typed retrieval candidate value object and a single canonical chunk key. Enforce owner scope in `SearchUseCase` and concrete Qdrant/Postgres adapters; use a separate service/port for the legal corpus. Make index invalidation explicit in document ingest/delete application services. Reject incomplete provenance rather than fabricating a key such as `"_"`.

## Related code files

`src/modules/retrieval/application/{dto,ports,search_use_case}.py`, `src/modules/retrieval/domain/services/{fusion,hybrid_search}.py`, `src/modules/retrieval/infrastructure/{vector/qdrant_store,keyword/bm25_manager,document_store/document_repository}.py`, `src/modules/document/application/{process,delete}.py`, `tests/test_retrieval_agent_reranking.py`.

## Implementation steps

1. Map every personal and legal caller of the current optional-user search API. Change the personal port to require a user ID; add explicit tests that `None` is rejected.
2. Normalize candidates from Qdrant and BM25 into the typed value object; include stable `chunk_id` or `(document_id, chunk_index)` and verified owner.
3. Update RRF keying to skip malformed candidates and preserve score provenance without duplicating a chunk.
4. Verify BM25 rebuild after restart, upload, delete, and failed ingestion with two users. Verify filename lookup by owner, not only by document ID.

## Todo list

- [ ] Require owner scope at personal search boundary.
- [ ] Define canonical chunk identity and provenance.
- [ ] Harden fusion and BM25 invalidation.
- [ ] Add two-tenant and lifecycle regressions.

## Success criteria

No unscoped personal query is callable through the application use case. Two-user tests show no cross-user chunks or titles, including after index rebuild and document deletion. Every fused hit has a stable source key.

## Risk assessment

Rejecting malformed legacy payloads may reduce recall until old Qdrant points are repaired. Count and log rejected candidates; provide an index migration/backfill path before enforcing the rule in production.

## Security considerations

Owner filtering belongs in the data adapter as well as the use case. Treat Qdrant payload IDs and client-supplied document IDs as untrusted. Do not expose another user's filename in enrichment.

## Next steps

Proceed to [Phase 02](phase-02-query-fusion-and-rerank.md) once source identity is stable.
