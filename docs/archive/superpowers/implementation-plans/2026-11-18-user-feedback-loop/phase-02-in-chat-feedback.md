# Phase 02 — Capture feedback inside the conversation

## Context links

- [Parent plan](plan.md); [Phase 01](phase-01-feedback-data-and-api.md); [Plan 4](../2026-11-18-chat-ui-ux/plan.md)
- [Chat UI](../../../../frontend/src/components/simple/SimpleChat.tsx); [chat client](../../../../frontend/src/lib/api/simple-client.ts); [message API DTO](../../../../src/modules/chat/api/responses.py)

## Overview

- Date: 2026-11-18; priority: P2; implementation: pending; review: pending; dependency: Phase 01 API and Plan 4 message design.

## Key insights

The feedback control should attach to a stable saved message ID. A provisional preview may be rejected or replaced; rating it as if it were a final answer would corrupt the signal. An optional reason is more actionable than a single binary vote, while mandatory comments would add friction.

## Requirements

1. Show compact thumbs up/down controls only on finalized, persisted assistant messages, including historical messages after reload.
2. After a downvote, offer optional reason chips such as incorrect, missing source, wrong source, irrelevant, slow, and other; allow a short optional comment. Keep wording and reason enum aligned with the backend.
3. Allow users to change or clear a vote. Display pending, saved, and failed states with a retry path; do not silently claim a failed submission succeeded.
4. Keep keyboard navigation, visible focus, accessible names, and touch targets usable on mobile. Do not interrupt reading or scrolling to solicit feedback.
5. Avoid copying private document text into feedback payloads. If later collecting corrected answers, require a separate explicit consent flow; that is outside this phase.

## Architecture

Create a typed `MessageFeedback` component fed by message ID and current rating. Put mutation and cache update in a focused hook/API client using Zod schemas. Optimistic UI may show pending state, but rollback on failure and reconcile with the server response. The component is placed in Plan 4's message action area and is independent of streaming event parsing.

## Related code files

`frontend/src/components/simple/SimpleChat.tsx`, `frontend/src/components/streaming/`, `frontend/src/lib/api/simple-client.ts`, `frontend/src/lib/hooks/`, `frontend/src/components/ui/`.

## Implementation steps

1. Define a strict frontend schema from the Phase 01 API contract; map persisted message IDs and feedback state when history loads.
2. Build the compact control and reason popover/sheet with shared UI primitives. Add clear label text and optional comment length counter.
3. Add mutation hook with pending, success, failure, retry, change, and clear behavior. Reconcile optimistic state with returned server value.
4. Ensure Plan 1 provisional/rejected/stopped states never render active rating controls and that final replacement does not duplicate controls.
5. Test keyboard/touch behavior, historical reload, optimistic rollback, 401/403/network errors, vote changes, and multiple messages. Run frontend gates.

## Todo list

- [ ] API schema and message feedback state mapping.
- [ ] Accessible up/down and optional reason UI.
- [ ] Mutation/retry/clear behavior.
- [ ] Final-only and failure-path tests.

## Success criteria

A user can rate a saved answer in one action, add an optional reason, change or clear the vote, and see the same state after reload. An unsaved preview never accepts a rating. A failed write is visibly recoverable.

## Risk assessment

Optimistic state can drift when a stream completes while conversation history reloads. Key feedback by persisted message ID and reconcile from server responses; do not key it by list position.

## Security considerations

Use the existing authenticated client path. Never trust client-visible owner checks as authorization; the Phase 01 API must enforce them. Render comments as plain text and avoid analytics events containing comment content.

## Next steps

Turn feedback into a reviewable improvement loop in [Phase 03](phase-03-triage-and-learning-policy.md).
