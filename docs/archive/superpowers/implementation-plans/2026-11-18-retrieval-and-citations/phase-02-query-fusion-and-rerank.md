# Phase 02 — Query execution, fusion, and reranking

## Context links

- [Parent plan](plan.md); [Phase 01](phase-01-scope-and-provenance.md)
- [Retrieval agent](../../../../src/modules/rag/orchestration/agents/retrieval_agent.py)
- [Hybrid search](../../../../src/modules/retrieval/domain/services/hybrid_search.py); [rerankers](../../../../src/modules/retrieval/domain/services/reranking)

## Overview

- Date: 2026-11-18; priority: P1; implementation: pending; review: pending; dependency: Phase 01 and Plan 2 query resolution.

## Key insights

Refinement can produce multiple queries but the retrieval call embeds and searches only the first. The hybrid service supports its own optional rerank, while RetrievalAgent calls it with `enable_rerank=False` and may rerank afterward. This makes the effective rerank policy hard to infer from a single setting.

## Requirements

1. Execute each selected query variant within a strict count and time budget, or remove the variant feature from the live configuration and documentation.
2. Fuse dense and BM25 candidates using stable chunk IDs and deterministic tie-breaking. Preserve branch scores for inspection.
3. Run exactly one configured reranker on the bounded candidate set; define a deterministic no-rerank fallback on timeout/error.
4. Use explicit minimum-evidence rules before generation; return a clear no-evidence result when nothing passes.
5. Record per-stage time, candidate count, and fallback reason without logging document text.

## Architecture

Move retrieval policy into one application service that accepts the standalone query from Plan 2. Keep dense, BM25, fusion, and reranker behind ports. Remove the module-level mutable `_llm_client` in `hybrid_search.py` when callers are migrated; pass dependencies through composition. Bound query variants and rerank candidates in configuration with one source of truth.

## Related code files

`src/modules/rag/orchestration/agents/retrieval_agent.py`, `src/modules/retrieval/application/search_use_case.py`, `src/modules/retrieval/domain/services/{hybrid_search,fusion}.py`, `src/modules/retrieval/domain/services/reranking/{llm_reranker,tei_reranker}.py`, `src/modules/retrieval/composition.py`, `src/config/{config.py,settings.yaml}`.

## Implementation steps

1. Write deterministic search fixtures for dense-only, BM25-only, both, duplicate chunks, multiple query variants, reranker failure, and no evidence.
2. Decide one live expansion policy: execute variants and fuse results, or disable the current placeholder. Remove settings that do nothing.
3. Consolidate rerank selection in one injected service. Keep TEI and LLM modes interchangeable, with timeout and bounded fallback.
4. Add a small trace with candidate counts and timings; compare selected chunks on fixtures before and after refactor.
5. Check the user filter remains present in every variant and fallback path.

## Todo list

- [ ] Resolve unused expansion settings.
- [ ] Stabilize multi-branch fusion and tie-breaking.
- [ ] Consolidate rerank and fallback policy.
- [ ] Test stage budgets and user filtering.

## Success criteria

The configured number of queries equals the number actually searched; every returned chunk has a source key; only one reranker runs; timeout falls back predictably. Fixture ranking changes are documented, and no unsupported hit is presented as strong evidence.

## Risk assessment

Multiple variants can increase cost and latency or over-retrieve weak matches. Start with a small cap and measure local stage timings. A reranker fallback may change ordering; surface the fallback in trace metadata.

## Security considerations

Apply `user_id` to every dense and BM25 search. Never feed unowned candidates to a reranker or LLM. Keep query variants and source text out of public logs.

## Next steps

Proceed to [Phase 03](phase-03-citation-binding.md) with normalized, ranked evidence.
