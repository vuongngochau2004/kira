# Phase 02 — SSE persistence and cancellation

## Context links

- [Parent plan](plan.md)
- [Phase 01](phase-01-graph-streaming-contract.md)
- [SSE endpoint](../../../../src/modules/chat/api/endpoints.py)
- [Chat use case](../../../../src/modules/chat/application/chat.py)
- [Next route](../../../../frontend/src/app/api/v1/chat/stream/route.ts)

## Overview

- Date: 2026-11-18
- Priority: P1
- Implementation status: Implemented
- Review status: Code review findings addressed; runtime smoke check pending
- Dependency: Phase 01

## Key insights

The endpoint appends each `content` chunk to the buffer that is later saved on `metadata`; provisional text must not enter that final buffer. The browser requests the same-origin `/api/v1/chat/stream` path, which has a dedicated Next route that forwards a backend fetch. Its upstream fetch currently has no `req.signal` linkage. Client abort alone does not prove provider cancellation.

## Requirements

1. Add `content_replace` to the SSE contract without changing existing non-RAG content events.
2. Save exactly the final replacement text with final citations; send `metadata` and `done` once on normal completion.
3. Propagate cancellation from browser through Next route, FastAPI streaming generator, graph iterator, and provider stream. Do not continue finalization or evaluation after cancellation.
4. A cancelled answer has no persisted user/assistant message pair; the client keeps a clearly marked local, unsaved preview. A later retry starts a fresh request.
5. Handle unexpected disconnects and explicit Stop identically. Treat cancellation as a distinct control path, not a generic server error.

## Architecture

The endpoint keeps two buffers: provisional display text and authoritative final text. Only `content_replace(provisional=false)` sets the final text eligible for `_save_streamed_messages`. The handler owns graph iterator cleanup; the endpoint owns SSE serialization. Pass `req.signal` to the upstream Next `fetch` and cancel the upstream response body when the downstream reader closes. In FastAPI, close the nested async iterator on `CancelledError`/disconnect; propagate cancellation without yielding SSE after disconnect. Use `finally` for cleanup, with idempotent close operations. Do not attempt a shielded DB save after cancellation.

## Related code files

- `src/modules/chat/api/endpoints.py`
- `src/modules/chat/application/chat.py`
- `src/modules/chat/infrastructure/handlers/rag_handler.py`
- `src/modules/rag/orchestration/graph/langgraph_pipeline.py`
- `frontend/src/app/api/v1/chat/stream/route.ts`
- `tests/test_security_upload_and_stream.py`

## Implementation steps

1. Centralize SSE serialization for the added event type; ensure JSON schema and event names match the frontend union.
2. Make final response replacement overwrite the persistence buffer. Enforce one metadata save and one normal done event.
3. Wire downstream abort to upstream fetch/body cancellation in the Next route; verify route precedence over rewrites in a local integration test.
4. Add cancellation cleanup across FastAPI, handler, graph, and provider. Verify the actual provider adapter cancellation behavior; close streams explicitly where supported.
5. Test normal, retry, rejection, provider failure, explicit abort, and disconnect with fake async streams. Assert no model tokens after cancellation and no message pair saved.

## Todo list

- [x] Separate provisional and final response buffers.
- [x] Serialize `content_replace` and retain the existing SSE events.
- [x] Wire Next and FastAPI cancellation to provider cleanup.
- [x] Add focused SSE persistence/cancellation tests.

## Success criteria

- Saved assistant content exactly equals the final replacement, including after regeneration or rejection.
- Cancelling mid-generation stops upstream iteration and leaves no saved partial pair.
- Normal completion emits exactly one `metadata` and one `done`; an error is safe to display and cannot persist draft text.
- No hanging provider task remains after client abort in the fake integration scenario.

## Risk assessment

Connection cancellation races with final save. Define the persistence boundary as the start of the atomic message-pair save; if save has committed, a late Stop cannot undo it. Test this race and make the UI show the server result if metadata already arrived. Validate actual ASGI and Next behavior because framework disconnect semantics can differ.

## Security considerations

Continue checking conversation ownership before streaming. Never send raw provider errors to the client. Ensure cleanup does not hold a DB session or provider connection after disconnect.

## Next steps

Proceed to [Phase 03](phase-03-frontend-and-verification.md) after the SSE contract is covered by tests.
