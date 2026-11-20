---
title: "Plan 3: Reliable retrieval and evidence-bound citations"
description: "Enforce tenant scope, use the queries and rerankers actually configured, and bind visible citations to answer evidence."
status: pending
priority: P1
effort: 6-9 days
branch: develop
tags: [retrieval, citations, security, rag]
created: 2026-11-18
---

# Goal

Make the chunks that reach generation relevant, traceable, and safe for each user. A visible citation must identify evidence actually used by the final answer, rather than merely a chunk retrieved nearby. This plan follows the stable streaming contract from [Plan 1](../2026-11-18-rag-streaming-and-cancellation/plan.md) and accepts the resolved query from [Plan 2](../2026-11-18-agent-core-and-routing/plan.md).

## Verified starting point

- Personal hybrid search combines Qdrant dense results and a per-user in-memory BM25 index through RRF; its `user_id` argument is optional, and Qdrant applies a user filter only when a user ID is supplied ([hybrid search](../../../../src/modules/retrieval/domain/services/hybrid_search.py#L80), [BM25 manager](../../../../src/modules/retrieval/infrastructure/keyword/bm25_manager.py#L10), [Qdrant](../../../../src/modules/retrieval/infrastructure/vector/qdrant_store.py#L104)). The live RAG caller currently passes `user_id`, but the port permits an unscoped personal search.
- RetrievalAgent's LLM expansion branch is a TODO; its document search uses only the first query even after synonym expansion ([refinement](../../../../src/modules/rag/orchestration/agents/retrieval_agent.py#L278), [search](../../../../src/modules/rag/orchestration/agents/retrieval_agent.py#L350)). This plan must either execute multiple queries or remove misleading expansion settings.
- Generation currently creates citations for every selected document; it does not prove which claims each chunk supports ([citation extraction](../../../../src/modules/rag/orchestration/agents/generation_agent.py#L669)). Final relevance checks can clear all citations but do not bind individual claims to chunks ([finalize](../../../../src/modules/rag/application/pipeline.py#L51)).

## Decisions

Require `user_id` for the personal-document retrieval use case and keep legal-corpus retrieval on an explicit, separate port. Normalize a stable chunk key and source provenance before fusion. Prefer one rerank stage with a timeout and a deterministic fallback. Use the final answer's valid source references to select citations; do not present every retrieved chunk as cited. Preserve the ability to show extra retrieved context in a separate “related sources” view only if clearly labeled.

## Phases

| Phase | Scope | Status | Effort |
|---|---|---|---|
| [01](phase-01-scope-and-provenance.md) | Tenant guardrails, stable chunk identities, index consistency | Pending | 2-3 days |
| [02](phase-02-query-fusion-and-rerank.md) | Honest query execution, fusion, one rerank policy | Pending | 2-3 days |
| [03](phase-03-citation-binding.md) | Claim/source binding, final citation contract, preview | Pending | 2-3 days |

## Acceptance

Tests with two users and overlapping document IDs never return cross-user chunks or filenames. A query-expansion setting either causes each selected query to run or is removed. Duplicate dense/BM25 hits fuse into one stable chunk. A final answer with one valid source reference shows that source only; unknown references are rejected; a grounded refusal has no misleading citations. The UI opens the cited page/chunk after final metadata. Use small deterministic evidence fixtures now; defer a broad scorecard until real usage data exists.

## Explicit deferrals

- Do not add a new search engine, knowledge graph, vector database, or generic agent tool loop.
- Defer corpus-wide relevance tuning and benchmark claims until a representative dataset is available.
- Do not collapse legal QA's version-specific citations into personal-document citation format.
