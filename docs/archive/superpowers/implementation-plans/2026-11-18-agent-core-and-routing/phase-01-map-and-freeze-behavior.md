# Phase 01 — Map and freeze live behavior

## Context links

- [Parent plan](plan.md); [Plan 1 contract](../2026-11-18-rag-streaming-and-cancellation/plan.md)
- [Chat graph](../../../../src/modules/chat/application/graph.py); [DI composition](../../../../src/modules/chat/composition.py)
- [RAG graph](../../../../src/modules/rag/orchestration/graph/langgraph_pipeline.py); [orchestrator agent](../../../../src/modules/rag/orchestration/agents/orchestrator_agent.py)

## Overview

- Date: 2026-11-18; priority: P1; implementation: in progress; review: pending; dependency: Plan 1 contract.

## Key insights

There are two orchestration shapes in the repository: ChatGraph routes handlers; LangGraph runs personal RAG; OrchestratorAgent also has a manual agent loop. The actual production entrypoint must be traced before deleting any code. Static comments and architecture diagrams are insufficient evidence of a live path.

## Requirements

1. Document the live calls from `/api/v1/chat/stream` and non-stream `/api/v1/chat/` to each handler and graph node.
2. Record each model call by stage, duration, outcome, and request ID without logging prompts or document text.
3. Characterize current route and quality behavior with deterministic fake classifier, retrieval, and LLM fixtures.
4. Identify all callers of `OrchestratorAgent.handle`, `handle_stream`, `GenerationAgent.handle_stream`, and legacy chat hooks before any removal.
5. Inspect the live agent/routing code and technical docs of Dify, RAGFlow, AnythingLLM, and Open WebUI at pinned commits. Compare their history handling, retrieval handoff, tool/agent loop limits, stream contract, retries, and citation finalization to KIRA; label docs-only behavior as unverified.

## Architecture

Put stage timing at application/graph boundaries, with a small typed trace object propagated through existing request context. Keep it request-scoped. Expose only bounded status fields through SSE. Reuse Plan 1's status events; do not add a second trace protocol.

## Related code files

`src/modules/chat/api/endpoints.py`, `src/modules/chat/application/{chat,graph}.py`, `src/modules/chat/composition.py`, `src/modules/classification/application/use_case.py`, `src/modules/rag/orchestration/graph/langgraph_pipeline.py`, `src/modules/rag/orchestration/agents/orchestrator_agent.py`, `tests/test_rag_quality_gate.py`, `tests/test_legal_chat_handler.py`.

## Implementation steps

1. Trace call sites and construct a routing matrix for personal RAG, conversation, drafting, and legal QA. Mark dead paths only after confirming no runtime DI caller.
2. Add a request-scoped stage trace and model-call counter. Do not persist raw prompts or retrieved chunks in logs.
3. Add scenario fixtures for route choice, quality retry, fallback, stream/non-stream parity, and cancellation; measure baseline stage times with a delayed fake LLM and one local service run if available.
4. Write a short decision record naming paths safe to consolidate in Phase 03 and behavior that must remain.
5. Create a competitor-code evidence ledger with repository URL, commit, file path, observed call path, and applicability to KIRA. Borrow a pattern only when it solves a measured KIRA failure; record trade-offs and licensing before copying code.

## Todo list

- [x] Trace production wiring and legacy callers.
- [x] Add bounded stage/model-call observability.
- [x] Pin route/quality behavior in focused tests.
- [ ] Record local provider baseline and consolidation decision. The decision is recorded; no local provider is running.
- [ ] Complete the full cross-project comparison. Pinned code observations are recorded for all four projects; uninspected behavior is labeled in the evidence ledger.

## Success criteria

The routing matrix points to live code, fixtures pass without external AI services, and one request can be followed across classification, retrieval, generation, quality, and finalize. The comparison cites actual code paths for each rival project and distinguishes measured timings, code-confirmed behavior, documentation claims, and estimates.

## Risk assessment

A seemingly unused method may be called by evaluation or CLI code. Search all callers and run their tests before removal. Instrumentation may increase log volume; keep fields bounded.

## Security considerations

Never log credentials, message bodies, prompts, document excerpts, or free-text model critiques. Trace IDs must not become authorization tokens.

## Next steps

Proceed to [Phase 02](phase-02-follow-up-context-and-routing.md) with the routing fixtures as the safety net.
