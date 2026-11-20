# Phase 03 — Frontend behavior and verification

## Context links

- [Parent plan](plan.md)
- [Phase 02](phase-02-sse-cancellation.md)
- [SSE client](../../../../frontend/src/lib/api/simple-client.ts)
- [Streaming state builder](../../../../frontend/src/lib/streaming/streaming-state-builder.ts)
- [Chat hook](../../../../frontend/src/lib/hooks/use-simple-chat.ts)
- [Chat UI](../../../../frontend/src/components/simple/SimpleChat.tsx)

## Overview

- Date: 2026-11-18
- Priority: P1
- Implementation status: Implemented; browser smoke check pending
- Review status: First-message Stop race fixed; browser and backend checks pending
- Dependency: Phase 02

## Key insights

The current state builder appends all content. Stop aborts the request and immediately finishes the current assistant message, so the UI does not distinguish a completed answer from a stopped preview. Stage events already exist and can supply progress labels without a broad redesign.

## Requirements

1. Show provisional personal RAG text as it arrives, visibly labeled “Đang kiểm tra câu trả lời”. Do not render citations until final metadata arrives.
2. `content_replace` must replace, never append. A retry clears the previous attempt. Final replacement removes the provisional label.
3. Show short, readable stage labels for routing, retrieval, generation, verification, and retry. Keep detailed trace optional and avoid layout jumps.
4. Stop must immediately switch to a stopped, unsaved local state, remain clickable during long stages, and prevent stale events from updating a new request.
5. Legal QA and non-RAG streams retain their existing final-content behavior. Handle missing or malformed SSE events without crashing the chat view.

## Architecture

Extend the typed SSE event union and runtime parsing in `simple-client.ts`. Add explicit message states such as `provisional`, `final`, `stopped`, and `error` to the streaming state builder and hook; use one active request ID to ignore late events. Keep this change within the existing chat UI and shared components. Render citation controls only from final metadata, and make the preview/Stop status accessible to screen readers.

## Related code files

- `frontend/src/lib/api/simple-client.ts`
- `frontend/src/lib/streaming/streaming-state-builder.ts`
- `frontend/src/lib/hooks/use-simple-chat.ts`
- `frontend/src/components/simple/SimpleChat.tsx`
- Existing frontend chat and streaming tests under `frontend/src/`

## Implementation steps

1. Add `content_replace` validation and parsing; reject impossible payloads gracefully.
2. Update state builder for provisional token append, attempt reset, final replacement, and stopped/error state.
3. Update chat hook so Stop aborts the active request and marks the preview stopped and unsaved. Preserve the final server result when metadata was already received.
4. Add compact stage status and accessible provisional/final labels in the current chat components.
5. Exercise normal generation, retry, rejection, early Stop, late Stop, and legal QA in component tests and a local browser smoke check. Record time to first provisional token and provider stop behavior with delayed fake streams; avoid claiming production latency gains from unit tests.

## Todo list

- [x] Parse and type the new SSE event.
- [x] Build attempt-aware message state and Stop behavior.
- [x] Add visible, accessible stage and provisional labels.
- [x] Run focused tests, including Stop during first conversation creation; a local browser smoke check remains open.
- [ ] Run required repository checks without unrelated baseline failures before any commit.

## Success criteria

- A user sees a provisional token before quality/finalize completes; retry replaces the earlier preview without duplicate text.
- Citation controls appear only after final metadata. Rejection replaces the preview with the safe final answer.
- Stop immediately updates the UI; the browser request, Next proxy, FastAPI iterator, and fake provider all close.
- `ruff check src/ tests/`, `ruff format --check src/ tests/`, `mypy src/`, `pytest tests/ -v`, `npm run lint`, `npx tsc --noEmit`, and `npm test` pass before commit.

## Risk assessment

The provisional label must be unmistakable, especially if a final answer later rejects the draft. Keep the wording short and test at mobile width. Large token volumes can cause excessive React updates; batch rendering on animation frames without delaying the backend stream.

## Security considerations

Never render untrusted model text as raw HTML. Do not expose provisional citations or hidden reasoning. Discard late events from a cancelled request so they cannot contaminate another conversation.

## Next steps

Latest verification: frontend lint and TypeScript checks pass; 78 frontend tests pass. The test run still emits a React controlled-input warning from the unrelated legal upload form. Backend verification remains open in this environment because `ruff` and `mypy` are unavailable; the default pytest plugin requires a socket that the sandbox denies. The frontend is not running on port 3001, so browser smoke verification has not been performed. No commit was made.

After this plan is implemented and observed with real users, prioritize the separate chat UI redesign and feedback collection plans. Formal dataset-based evaluation remains later work.
