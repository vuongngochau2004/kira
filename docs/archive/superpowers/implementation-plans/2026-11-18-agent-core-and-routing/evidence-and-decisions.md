# Plan 2 implementation evidence and decisions

Date: 2026-11-18. This record distinguishes inspected code from measured behavior. No external code was copied.

## Live KIRA call path

| Entry | Route | Personal RAG path | Finalization |
|---|---|---|---|
| `POST /api/v1/chat/completions` | `ChatUseCase.execute` → `ChatGraph.run` → classifier → handler | `RAGHandler.handle` → `RAGPipelineService.execute` → compiled `LangGraphRAGPipeline.run` | `RAGPipelineService.finalize`, then saved message pair |
| `POST /api/v1/chat/stream` | `_stream_generator` → `ChatUseCase.execute_stream` → `ChatGraph.run_stream` → classifier → handler | `RAGHandler.handle_stream` → `RAGPipelineService.run_stream` → compiled `LangGraphRAGPipeline.run_stream` | Same `finalize`; only authoritative replacement is saved |

The chat graph selects conversational, drafting, legal QA, or personal RAG handlers. The RAG graph owns orchestrator routing, retrieval, generation, quality, retry, and fallback. Static search of `src/`, `tests/`, `scripts/`, and `training/` found no caller of `OrchestratorAgent.handle_stream` or the old manual agent execution path. The orchestrator class now records routing only; the compiled graph executes all later nodes.

History is read through a query that joins messages to a conversation with matching authenticated `user_id` and excludes deleted conversations. It takes the latest eight saved user/assistant messages and clips the request context to 4,000 characters. Stream cancellation saves no partial assistant turn, so cancelled preview text is unavailable to later requests. A pronoun-based follow-up uses the most recent standalone user question as retrieval context; the original query remains in state for the answer.

## Quality checks and budgets

| Stage | Input and output | Distinct purpose | Budget |
|---|---|---|---|
| Classification | Current question, route | Select handler; legal-corpus cue precedes generic file keywords | Existing classifier timeout |
| Retrieval | Resolved query, authenticated user ID → chunks | Find user-owned evidence | `RetrievalAgentConfig.timeout_ms` |
| Generation | Original question, resolved referent, retrieved chunks → draft | Produce answer | `GenerationAgentConfig.timeout_ms` |
| Quality | Draft, resolved question, chunks → critique and verification | Gate retry/fallback before finalization | `QualityAgentConfig.timeout_ms` |
| Final relevance | Approved draft and bounded evidence → accept/reject | Extra answer-to-question relevance check | `rag_finalization_timeout_seconds` (default 30) |

The quality check and final relevance check receive different inputs and can catch different failures. There is no local latency or false-positive measurement to justify removing either. On timeout or provider failure, final relevance rejects the answer and clears citations. Graph retries remain capped by `max_pipeline_iterations`. Existing Plan 1 cancellation closes the upstream stream and provider iterator.

`ChatGraph` creates a request-local trace ID. Classification, graph nodes, and finalization log bounded stage durations. The provider-neutral RAG LLM wrapper and classifier LLM strategy count calls by stage with outcome and duration; logs contain no prompt or retrieved text.

## External code evidence

| Project and pinned code | Verified observation | Applicability and limit |
|---|---|---|
| [Dify agent node at `50aa7f0`](https://github.com/langgenius/dify/blob/50aa7f0b5e6fe235aab6c6a9d0d608a62176b954/api/core/workflow/nodes/agent_v2/agent_node.py#L488) | The agent node consumes backend stream events and emits text chunks; the same file imports citation extraction and failure orchestration. | Supports keeping stream output and finalization policy explicit. This file alone does not establish history ownership or citation correctness. |
| [RAGFlow agent at `2f22bb0`](https://github.com/infiniflow/ragflow/blob/2f22bb0a1a806f66009e1426bed40ea7e115debb/internal/agentic_rag/agent.go#L57) | Input carries compact conversation messages, `MaxIterations`, tenant ID, dataset IDs, document IDs, and a stream flag. | Supports bounded history and scope entering the agent at one boundary. KIRA has no need for its ReAct tool loop. |
| [AnythingLLM chat container at `64b599f`](https://github.com/Mintplex-Labs/anything-llm/blob/64b599fc92a9c2f4d60f2f9244d278acfff73204/frontend/src/components/WorkspaceChat/ChatContainer/index.jsx#L373) | The UI keeps known history in component state and closes its WebSocket on the abort event. | Confirms a visible Stop path; this frontend file does not prove server cancellation or persistence semantics. |
| [Open WebUI chat model at `0666e59`](https://github.com/open-webui/open-webui/blob/0666e59d26a4d056e0bacee41742486badd71cf8/backend/open_webui/models/chats.py#L2015) | `get_chat_by_id_and_user_id` filters by both chat ID and user ID. | Supports KIRA's owner-scoped history query; this file does not establish retrieval or agent loop behavior. |

These links are code observations at fixed commits, not benchmark results. No licensing review is needed for copied code because no external code was copied.

## Verification and remaining evidence

Focused deterministic tests cover follow-up resolution, history budget and owner predicate, legal precedence, quality retry/fallback, provider failure, request-level model-call counts, stream/non-stream answer-and-citation parity, and SSE cancellation/persistence. The final focused run passed 64 tests with eight existing Pydantic deprecation warnings. An actual-provider benchmark and a two-user database integration test remain before the parent plan can be marked implemented. `localhost:8006` did not accept a connection, and `docker compose ps` reported no running services. The full security test module currently stalls on its first upload-reader case in this sandbox; five selected SSE tests pass. Ruff and mypy executables are not installed in the available virtual environment.
