# Phase 02 — Follow-up context and safe routing

## Context links

- [Parent plan](plan.md); [Phase 01](phase-01-map-and-freeze-behavior.md)
- [Endpoint history loading](../../../../src/modules/chat/api/endpoints.py); [ChatQuery](../../../../src/modules/chat/application/dto.py)
- [Classification chain](../../../../src/modules/classification/domain/strategies/composite.py); [RAG state](../../../../src/modules/rag/orchestration/state/rag_state.py)

## Overview

- Date: 2026-11-18; priority: P1; implementation: in progress; review: pending; dependency: Phase 01.

## Key insights

History is present in the chat layer but absent from the personal RAG graph inputs. A user asking “What about its effective date?” may therefore retrieve on the bare pronoun. Routing also has keyword precedence and an error fallback to RAG; those choices need explicit fixtures, especially where a user's file question mentions a law.

## Requirements

1. Load history only from a conversation already verified to belong to the authenticated user; cap by turn count and characters/tokens.
2. Resolve anaphoric follow-ups into a standalone retrieval query while retaining the user's original wording for the answer. A failed rewrite falls back to the original query and a visible, safe status.
3. Preserve legal QA precedence for legal-corpus questions and personal RAG precedence for questions about the user's uploaded file, even if the file mentions law.
4. Do not let history from a stopped, unsaved prompt or another conversation enter retrieval.
5. Avoid an extra rewrite LLM call for questions that already stand alone; use a deterministic fast path, then a bounded optional model call.

## Architecture

Extend the application DTO and RAG workflow port with a typed, bounded history value. Introduce a query-resolution use case/port between classification and retrieval; give it only prior user/assistant turns and the current query, never full raw document chunks. Store `original_query` and `retrieval_query` separately in request state. Maintain `user_id` on every search. Keep routing rules in the classifier composition, not FastAPI endpoints.

## Related code files

`src/modules/chat/api/endpoints.py`, `src/modules/chat/application/{dto,graph}.py`, `src/modules/classification/domain/strategies/{keyword,legal,composite,llm}.py`, `src/modules/rag/application/{pipeline,ports}.py`, `src/modules/rag/orchestration/{state/rag_state,agents/retrieval_agent,graph/langgraph_pipeline}.py`.

## Implementation steps

1. Define the maximum history budget and a typed list of recent turns. Load by authenticated `conversation_id` and trim at the application boundary.
2. Add a pure follow-up detector and standalone-query resolver behind a port. Keep the original query for answer wording and feedback capture.
3. Pass the resolved query to embedding/BM25; use the original query plus a short, relevant history summary in generation. Never include prior assistant citations as unquestioned evidence.
4. Refine classifier precedence with explicit route tests: conversational, personal file, drafting, legal, ambiguous, classifier failure. Make fallback behavior deliberate and observable.
5. Test two-user and two-conversation isolation, stopped-turn exclusion, failed rewrite, and stream/non-stream parity.

## Todo list

- [x] Define history budget and ownership boundary.
- [x] Implement deterministic standalone-query resolution.
- [x] Pass history and resolved query through ports/state.
- [x] Lock route precedence and fallback in focused tests.
- [ ] Verify two-user isolation against a running database.

## Success criteria

Pronoun-based follow-ups retrieve from the prior topic in deterministic tests; a first-turn question does not trigger a rewrite call. A user cannot influence another user's retrieval through history. Legal and drafting routes remain correct.

## Risk assessment

Rewrite can invent facts or change intent. It must only produce a search query and must never be treated as evidence. If uncertain, use the original query and show a limited-context response.

## Security considerations

Enforce ownership before loading history; keep history bounded and request-local. Reject client-supplied user IDs and avoid logging conversation content.

## Next steps

Proceed to [Phase 03](phase-03-simplify-and-budget-workflow.md) after follow-up and routing tests pass.
