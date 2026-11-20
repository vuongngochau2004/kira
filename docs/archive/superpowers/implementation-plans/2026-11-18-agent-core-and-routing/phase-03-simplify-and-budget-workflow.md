# Phase 03 — Simplify and budget the workflow

## Context links

- [Parent plan](plan.md); [Phase 01](phase-01-map-and-freeze-behavior.md); [Phase 02](phase-02-follow-up-context-and-routing.md)
- [Compiled RAG graph](../../../../src/modules/rag/orchestration/graph/langgraph_pipeline.py)
- [Manual orchestrator](../../../../src/modules/rag/orchestration/agents/orchestrator_agent.py); [finalize](../../../../src/modules/rag/application/pipeline.py)

## Overview

- Date: 2026-11-18; priority: P1; implementation: in progress; review: pending; dependency: Phases 01-02.

## Key insights

The graph quality node controls retry/fallback, while `OrchestratorAgent.handle` has a second loop. Final relevance checking can add another model call after graph quality. Simplification should be driven by the Phase 01 trace and parity fixtures, not by deleting safeguards on sight.

## Requirements

1. One production orchestration path for personal RAG, shared by stream and non-stream completion.
2. Explicit budgets for rewrite, rerank, generation retries, quality checks, and final relevance; a cancellation or timeout stops downstream calls.
3. Preserve final verified-only persistence and provisional preview semantics from Plan 1.
4. Keep legal QA and drafting flows separate; do not silently route them through the personal RAG graph.
5. If the same check runs twice, either remove the redundant call after parity evidence or explain its distinct purpose and measurable failure mode.

## Architecture

Treat LangGraph as the single personal-RAG workflow. Extract routing-only policy from `OrchestratorAgent` if still needed, then remove unused manual execution methods after caller and test audit. Keep quality decision rules in one typed policy object. Stage budgets live in configuration; the graph/LLM ports enforce them. Finalizer remains the sole authority for public answer/citations.

## Related code files

`src/modules/rag/orchestration/{graph/langgraph_pipeline,agents/orchestrator_agent,agents/quality_agent,state/rag_state}.py`, `src/modules/rag/application/pipeline.py`, `src/config/{config.py,settings.yaml}`, `src/modules/chat/infrastructure/handlers/rag_handler.py`, `tests/test_rag_quality_gate.py`.

## Implementation steps

1. Compare Phase 01 stage call counts and failure cases. Create a table of each check's input, output, latency, and unique responsibility.
2. Move routing policy into a small pure function or typed service; make the compiled graph call it. Remove only manual paths proven unused, with tests for CLI/evaluation callers.
3. Add stage budgets and cancellation propagation for every LLM call. Ensure timeout fallback is a safe final message with no unsupported citations.
4. Make stream and non-stream use the same finalization rules; test the same fake sequence through both entrypoints.
5. Re-run route, quality, legal, drafting, provider failure, and Stop regressions. Compare model-call count and stage latency against Phase 01 baseline; record actual numbers.

## Todo list

- [ ] Decide duplicated checks from measured evidence; both remain until a provider benchmark is available.
- [x] Consolidate production orchestration.
- [x] Enforce per-stage budgets and cancellation.
- [ ] Record a real-provider call-count and latency delta. Deterministic stream/non-stream parity passes.

## Success criteria

No duplicate production agent loop remains; stream/non-stream final answers and citations agree; retries are bounded; Stop ends all downstream work. The call-count change and latency effect are measured, with no quality regression in the pinned scenarios.

## Risk assessment

Removing a check can reduce latency while weakening rejection behavior. Preserve a rollback switch until fixture parity and local smoke checks pass. Do not turn a timed-out quality check into an accepted answer.

## Security considerations

Failure and timeout messages must not contain model prompts, hidden critique, or retrieved document text. User scope must survive retries and rewritten queries.

## Next steps

Hand the stable retrieval query and finalization contract to [Plan 3](../2026-11-18-retrieval-and-citations/plan.md).
