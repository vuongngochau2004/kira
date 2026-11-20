---
title: "Plan 1: Responsive RAG streaming and real cancellation"
description: "Stream provisional personal-document RAG answers, preserve final quality checks, and propagate cancellation through the request chain."
status: implemented
priority: P1
effort: 4-6 days
branch: develop
tags: [rag, chat, streaming, frontend]
created: 2026-11-18
---

# Goal

Make personal-document RAG feel responsive: show generation as it happens, explain long-running stages, and stop backend work when the user presses Stop. Keep the LangGraph quality and regeneration path. This is a standalone plan for proposal 1; implementation and broader UI redesign belong to later work.

## Verified starting point

- The graph runs generation, quality, and possible regeneration; `run_stream` currently emits graph updates and message events ([graph](../../../../src/modules/rag/orchestration/graph/langgraph_pipeline.py#L96)).
- The generation agent has a streaming method, but the graph generation node calls its non-streaming `handle`; the RAG chat handler ignores message events and emits answer text only after `finalize`, which can run another relevance check ([generation agent](../../../../src/modules/rag/orchestration/agents/generation_agent.py#L284), [RAG handler](../../../../src/modules/chat/infrastructure/handlers/rag_handler.py#L57), [finalize](../../../../src/modules/rag/application/pipeline.py#L46)).
- The SSE endpoint saves a response when it handles `metadata`; the browser Stop action aborts its fetch and marks the local message complete ([endpoint](../../../../src/modules/chat/api/endpoints.py#L496), [hook](../../../../frontend/src/lib/hooks/use-simple-chat.ts#L575)).
- A security regression test explicitly requires no unverified draft text to be emitted ([test](../../../../tests/test_security_upload_and_stream.py#L100)). The proposed preview policy changes this behavior for ordinary RAG and requires an intentional test update. Legal QA retains verified-only output.

## Product and safety decision

For **personal-document RAG**, stream generated text as a visibly provisional preview. On quality retry, clear the previous preview before showing the new attempt. After graph completion and relevance checks, send one authoritative replacement containing the approved answer or safe rejection; persist only that final text and its verified citations. Never label a provisional preview as verified or attach citations to it. For **legal QA**, keep the current verified-only behavior because an unsupported interim answer has a higher cost. This is a deliberate trade-off: ordinary RAG users may briefly see text that is later replaced.

## Phases

| Phase | Scope | Status | Effort |
|---|---|---|---|
| [01](phase-01-graph-streaming-contract.md) | Graph token events, attempt boundaries, final replacement contract | Implemented; tests pass | 1.5-2 days |
| [02](phase-02-sse-cancellation.md) | SSE persistence boundary and cancellation propagation | Implemented; tests pass | 1-1.5 days |
| [03](phase-03-frontend-and-verification.md) | Provisional UI, Stop behavior, regression checks | Implemented; browser verification pending | 1.5-2.5 days |

## End-to-end contract

`routing` / `retrieval` / `status` remain as-is. Personal RAG adds `content` with `{text, provisional: true, attempt}` during generation and `content_replace` with `{text, provisional: false}` after finalization; `content_replace` with empty text clears a failed attempt. `metadata` follows the final replacement exactly once and carries final citations and message IDs; `done` follows once. On cancellation, do not send final metadata, persist no partial answer, and mark the local preview as stopped and unsaved. On failure, clear the provisional preview, emit a safe `error`, then `done`; do not persist a draft. Non-RAG handlers and legal QA keep their existing content semantics.

## Scope limits

- No new evaluation dataset, RLHF loop, retrieval redesign, provider replacement, or broad chat layout clone.
- No fake typing effect: tokens must originate from the provider stream.
- No extra model call merely to produce status text. Stage status uses existing graph events.

## Definition of done

With a delayed fake LLM, the first provisional RAG token reaches the SSE client before quality/finalize finishes; a retry replaces the previous attempt; only the final approved answer and citations are stored. Pressing Stop closes the browser stream and upstream graph/provider work and leaves no in-flight task or saved partial answer. Legal QA and existing non-RAG streams pass unchanged. Required backend and frontend checks pass before any commit.

## Implementation evidence and remaining checks

- The compiled graph now uses a custom event channel for provisional tokens, while the same generation attempt updates graph state and still passes through quality and final relevance checks. Targeted tests cover early tokens, retries, rejection, provider cancellation, and final-only persistence.
- The SSE endpoint buffers provisional and final content separately; the final answer and user message are saved in one transaction. Next.js forwards cancellation upstream. The UI marks a stopped preview as unsaved and shows citations only after final metadata.
- Backend test suite: 401 passed and 5 skipped in the final run. Mypy found no issues across 333 source files. Frontend lint, TypeScript, and 73 tests passed in the final run.
- A real-provider request and browser smoke check have not been performed; the running Docker images do not contain these source edits. Full repository Ruff lint reports 3 pre-existing errors in unrelated legal files, and full format check reports 7 unrelated files. Changed Python files pass targeted lint and format checks. No commit is included in this plan status.
