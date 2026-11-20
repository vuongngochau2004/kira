# Phase 01 — Store owner-scoped answer feedback

## Context links

- [Parent plan](plan.md); [Plan 1 SSE persistence](../2026-11-18-rag-streaming-and-cancellation/phase-02-sse-cancellation.md)
- [Conversation and message models](../../../../src/shared/infrastructure/persistence/database/models.py); [chat API](../../../../src/modules/chat/api/endpoints.py)

## Overview

- Date: 2026-11-18; priority: P2; implementation: pending; review: pending; dependency: persisted final assistant message IDs.

## Key insights

The current `Message` row has metadata but no durable, constrained rating record. Keeping feedback separate supports ownership checks, uniqueness, deletion, and later aggregation without overloading generated-answer metadata. The repository currently has SQL migration files under `migrations/`; verify the deployed migration path before adding a new migration.

## Requirements

1. Store at most one current feedback record per `(user_id, message_id)` with rating enum, optional reason enum, bounded optional comment, timestamps, and a unique constraint.
2. Accept feedback only for a persisted assistant message in a non-deleted conversation owned by the authenticated user. Reject user/system messages and unknown IDs without exposing ownership details.
3. Provide authenticated create/update/read/delete semantics (idempotent upsert or `PUT`, plus `DELETE`), using a stable API schema and explicit errors.
4. Deleting a conversation or user must delete or anonymize feedback according to the chosen retention policy. Migration rollback and index behavior must be documented.
5. Keep comments and private answer/document content out of logs and metrics. Limit field length and request rate.

## Architecture

Add a typed feedback entity and repository port inside `src/modules/chat/`, with a SQLAlchemy adapter and DB migration. The application use case checks ownership through a repository query joining message to conversation and scoped by `user_id`; the endpoint handles HTTP validation only. Expose feedback state in the message response or a batch endpoint to avoid one request per message. Use one transaction for ownership verification and upsert where possible.

## Related code files

`src/shared/infrastructure/persistence/database/models.py`, `migrations/`, `src/modules/chat/{domain,application,infrastructure,api}/`, `src/modules/chat/api/responses.py`, `src/server/main.py`, `tests/`.

## Implementation steps

1. Trace how SQL migrations run locally and in deployment; choose the next migration number and document forward/backward behavior.
2. Add `AnswerFeedback` schema with FK to message/user, uniqueness, constraints, cascade/retention decision, and appropriate indexes. Do not store answer snapshots by default.
3. Add repository port and use cases for owner-scoped fetch/upsert/delete. Validate assistant role, saved-final state, and non-deleted conversation before mutation.
4. Add Pydantic request/response schema and authenticated route(s); batch-load current user's feedback with conversation messages.
5. Test own/foreign/unknown message, deleted conversation, non-assistant role, duplicate submit, update, delete, malformed reason, oversized comment, and concurrent upsert. Run backend lint, format, type, and tests.

## Todo list

- [ ] Migration path and retention decision documented.
- [ ] Constrained feedback model, repository, and use cases.
- [ ] Authenticated API and batch read path.
- [ ] Ownership, idempotency, and migration tests.

## Success criteria

One current rating exists per user/message, repeated submissions are safe, and a foreign message cannot be probed or changed. Message-list reads do not introduce per-message queries. The migration and its rollback are exercised on a disposable database.

## Risk assessment

Concurrent upserts can race if uniqueness exists only in application code. Enforce uniqueness in PostgreSQL and handle conflict within the transaction. Existing deployments may use a different migration runner than README claims; inspect before shipping.

## Security considerations

Owner scope must be enforced in SQL, not inferred from client-supplied IDs. Rate-limit writes, bound comments, and avoid logging raw comments, document text, or source snippets. Decide whether comments may contain personal data and set deletion/retention behavior accordingly.

## Next steps

Add the in-chat control in [Phase 02](phase-02-in-chat-feedback.md).
