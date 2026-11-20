# Phase 01 — Graph streaming contract

## Context links

- [Parent plan](plan.md)
- [Graph](../../../../src/modules/rag/orchestration/graph/langgraph_pipeline.py)
- [Generation agent](../../../../src/modules/rag/orchestration/agents/generation_agent.py)
- [RAG handler](../../../../src/modules/chat/infrastructure/handlers/rag_handler.py)
- [Quality tests](../../../../tests/test_rag_quality_gate.py)

## Overview

- Date: 2026-11-18
- Priority: P1
- Implementation status: Implemented
- Review status: Code review findings addressed; runtime smoke check pending
- Dependency: None

## Key insights

`run_stream` executes the compiled LangGraph workflow; an earlier manual streaming path skipped the generation/quality regeneration loop. The current graph generation node awaits the full model response. The separate `GenerationAgent.handle_stream` is not connected to the graph. A provider stream must feed both graph state and token events without running generation twice.

## Requirements

1. Keep the existing graph topology, quality decision, retry limit, and final relevance filter.
2. Emit token events from the same generation attempt that updates graph state. Add an explicit attempt identifier so retries cannot mix text.
3. Report stage starts and completions with bounded, user-facing labels; do not expose raw internal reasoning or sensitive retrieved text.
4. Keep user-scoped retrieval and citation binding intact. Preview tokens carry no citation claim.

## Architecture

Use a typed internal event from the generation node through the installed LangGraph custom stream channel (verify the installed API before coding). The generation node consumes `LLMClientPort.stream`, accumulates its own final answer, emits each chunk with an attempt number, and writes that same answer to graph state. `RAGHandler` converts those custom events to provisional `content`. It emits a clearing `content_replace` at the start of each later attempt. After graph completion, `finalize` remains the only source of the authoritative `content_replace` and citations. If the installed LangGraph version lacks a suitable custom stream API, use a scoped queue tied to one graph invocation; do not hand-run agents outside the graph.

## Related code files

- `src/modules/rag/orchestration/graph/langgraph_pipeline.py`
- `src/modules/rag/orchestration/agents/generation_agent.py`
- `src/modules/chat/infrastructure/handlers/rag_handler.py`
- `src/modules/rag/application/pipeline.py`
- `tests/test_rag_quality_gate.py`
- `tests/test_security_upload_and_stream.py`

## Implementation steps

1. Pin down the installed LangGraph stream API and define a small typed internal token/attempt event; avoid reliance on a version range alone.
2. Refactor generation so graph execution uses one provider stream for both token emission and state update. Keep prompt construction and citation extraction shared with the non-stream path.
3. Translate graph events in `RAGHandler`: emit stage status, provisional tokens, attempt reset, then one final replacement after `finalize`.
4. Ensure quality rejection and graph error clear the preview. Keep terminal metadata citations empty on rejection.
5. Replace the old blanket no-draft test with two explicit contracts: personal RAG previews are marked and replaceable; legal/strict paths never expose previews. Preserve the error test's no-persisted-draft guarantee.

## Todo list

- [x] Confirm actual LangGraph custom stream support.
- [x] Add attempt-aware token emission from compiled graph.
- [x] Implement final replacement and retry clearing in the handler.
- [x] Update targeted graph/quality/security tests.

## Success criteria

- A fake provider yields two delayed chunks; the handler yields each before the quality node finishes.
- A failed first attempt is cleared before the second attempt; final content equals the graph's approved result.
- A rejected answer exposes no verified citations, and no draft is written as final content.
- Non-stream execution still returns the same final answer for the same fake model output.

## Risk assessment

Streaming a provisional answer changes the current verified-only disclosure guarantee. Make this visible in the UI and restrict it to ordinary personal RAG. A library-specific streaming hook may differ from the plan; verify locally and preserve graph execution in either implementation.

## Security considerations

Preserve `user_id` filtering in retrieval. Do not send prompt contents, hidden reasoning, or backend exception details in status or token metadata. Never put provisional citations into a persisted message.

## Next steps

Proceed to [Phase 02](phase-02-sse-cancellation.md) after the internal event contract and tests are stable.
