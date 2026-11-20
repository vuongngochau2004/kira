---
title: "Plan 2: Predictable, conversation-aware agent core"
description: "Make intent routing and LangGraph behavior explicit, preserve follow-up context, and remove duplicate orchestration only after parity tests."
status: in_progress
priority: P1
effort: 5-8 days
branch: develop
tags: [rag, classification, chat, orchestration]
created: 2026-11-18
---

# Goal

Improve the answers and interaction logic behind the chat UI without adding another agent framework. A follow-up question should use the right conversation context, select the right handler, and run a bounded workflow that can be explained and cancelled. This is a separate plan from [Plan 1](../2026-11-18-rag-streaming-and-cancellation/plan.md); it assumes Plan 1's SSE contract is stable.

## Verified starting point

- The chat graph classifies once and directly streams the selected handler ([chat graph](../../../../src/modules/chat/application/graph.py#L63)). `Classification` uses keyword and cached LLM strategies and falls back to RAG on classifier error ([classification](../../../../src/modules/classification/application/use_case.py#L52)).
- The endpoint loads previous messages and passes them as `conversation_history` in `ChatQuery`, but `RAGPipelineService` forwards only query, user ID, and conversation ID to its graph; the RAG state stores no history ([endpoint](../../../../src/modules/chat/api/endpoints.py#L534), [RAG pipeline](../../../../src/modules/rag/application/pipeline.py#L25), [state](../../../../src/modules/rag/orchestration/state/rag_state.py#L161)). Thus ordinary RAG follow-up grounding in prior turns is **not evidenced** by the code path.
- The compiled LangGraph graph already owns generation, quality, retry, and fallback. `OrchestratorAgent.handle` also contains a separate execution loop, bypassed when called as a graph node ([graph](../../../../src/modules/rag/orchestration/graph/langgraph_pipeline.py#L96), [orchestrator](../../../../src/modules/rag/orchestration/agents/orchestrator_agent.py#L87)). Do not delete it until callers and behavior are mapped.
- Finalization may call another LLM for relevance after graph quality checks ([finalize](../../../../src/modules/rag/application/pipeline.py#L102)); the extra latency and incremental value are **not measured**.

## Decisions

Keep the compiled graph as the single workflow for personal RAG. Pass a bounded, user-owned conversation summary or recent turns explicitly into routing and query resolution; keep retrieved document content out of cross-user state. Simplify only after tests prove equivalent legal, drafting, conversational, and personal-RAG routing. Do not add tool calling, web browsing, autonomous loops, or RLHF training in this plan.

## Phases

| Phase | Scope | Status | Effort |
|---|---|---|---|
| [01](phase-01-map-and-freeze-behavior.md) | Map live call graph, add trace and behavior fixtures | In progress; local benchmark pending | 1-2 days |
| [02](phase-02-follow-up-context-and-routing.md) | Bound history, resolve follow-ups, route safely | In progress; deterministic resolution and owner scope added | 2-3 days |
| [03](phase-03-simplify-and-budget-workflow.md) | Consolidate orchestration and bound model calls | In progress; full local benchmark pending | 2-3 days |

## Acceptance

Deterministic tests cover: a first document question, a pronoun-based follow-up, ordinary conversation, drafting, legal intent, no accessible document, provider failure, and Stop during every model stage. Follow-up retrieval uses only the authenticated user's conversation and documents. For identical fixtures, non-stream and stream paths end with the same final answer and citation policy. Per-stage timing and model-call count are visible in structured logs; no absolute latency promise is made without a local benchmark.

## Explicit deferrals

- Defer multi-agent autonomy, external tools, model fine-tuning, and new vector stores.
- Defer formal RAG scoring on a real dataset to a later, separate evaluation decision; use small behavior fixtures here to prevent regressions.
- Do not remove quality checks solely to shorten latency. Measure their cost and value first.

## Implementation record

The live call map, consolidation decision, pinned external-code observations, and remaining verification are in [evidence and decisions](evidence-and-decisions.md). Request-level call counts and deterministic stream/non-stream parity are covered. Do not mark this plan implemented until a local provider benchmark and two-user database check are recorded.
