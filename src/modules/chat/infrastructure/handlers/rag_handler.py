"""Chat transport adapter for the RAG application use case."""

import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from loguru import logger

from src.modules.rag.application import RAGExecutionResult, RAGPipelineService
from src.shared.domain.value_objects.citation import Citation
from src.shared.ports.classification import ClassificationResult, Intent
from src.shared.ports.handlers import HandlerConfig, HandlerResult, QueryHandlerBase


class RAGHandler(QueryHandlerBase):
    """Adapt the RAG bounded context to the chat handler port.

    This class deliberately contains only intent validation and translation to
    the chat transport contract. Workflow state, evidence validation and
    citation policy remain inside ``src.modules.rag.application``.
    """

    def __init__(
        self,
        rag_service: RAGPipelineService,
        config: HandlerConfig | None = None,
    ):
        self.config = config or HandlerConfig()
        self.rag_service = rag_service

    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None,
    ) -> HandlerResult:
        self._validate_intent(classification)
        try:
            result = await self.rag_service.execute(
                query=query,
                user_id=str(user_id),
                conversation_id=(context or {}).get("conversation_id"),
                **self._history_kwargs(context),
            )
            return self._to_handler_result(result)
        except Exception:
            logger.error("RAG execution failed: user_id={}", user_id)
            return HandlerResult(
                content="Có lỗi xảy ra khi xử lý câu hỏi.",
                citations=[],
                metadata={"handler": self.get_name()},
                status="error",
                error="RAG request failed",
            )

    async def handle_stream(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        try:
            self._validate_intent(classification)
        except ValueError as exc:
            yield {"type": "error", "data": {"error": str(exc)}}
            yield {"type": "done"}
            return

        yield {
            "type": "routing",
            "data": {
                "router": "agentic_rag",
                "intent": classification.intent.value,
                "confidence": classification.confidence,
            },
        }

        final_state: dict[str, Any] | None = None
        # Graph nodes run one after another, so the gap between two "updates" chunks is the
        # wall time of the node that just finished.
        step_started = time.perf_counter()
        preview_started = False
        stream = self.rag_service.run_stream(
            query=query,
            user_id=str(user_id),
            conversation_id=(context or {}).get("conversation_id"),
            **self._history_kwargs(context),
        )
        try:
            async for event in stream:
                mode = event.get("mode")
                chunk = event.get("chunk")
                if mode == "custom" and isinstance(chunk, dict):
                    attempt = chunk.get("attempt")
                    if chunk.get("kind") == "stage_start" and chunk.get("stage") in {
                        "retrieval",
                        "quality",
                    }:
                        yield {
                            "type": "status",
                            "data": {
                                "stage": chunk["stage"],
                                "metadata": {"state": "started"},
                            },
                        }
                    elif chunk.get("kind") == "attempt_start" and isinstance(attempt, int):
                        if preview_started:
                            yield {
                                "type": "content_replace",
                                "data": {"text": "", "provisional": True, "attempt": attempt},
                            }
                        preview_started = True
                        yield {
                            "type": "status",
                            "data": {"stage": "generation", "metadata": {"attempt": attempt}},
                        }
                    elif chunk.get("kind") == "token" and isinstance(chunk.get("text"), str):
                        yield {
                            "type": "content",
                            "data": {
                                "text": chunk["text"],
                                "provisional": True,
                                "attempt": attempt,
                            },
                        }
                elif mode == "updates" and isinstance(chunk, dict):
                    for stage, state in chunk.items():
                        if not isinstance(state, dict):
                            continue
                        final_state = state
                        now = time.perf_counter()
                        duration_ms = round((now - step_started) * 1000)
                        step_started = now
                        yield self._status_event(stage, state, duration_ms)
                elif mode == "error":
                    logger.error("RAG stream emitted a workflow error")
                    if preview_started:
                        yield {"type": "content_replace", "data": {"text": "", "provisional": True}}
                    yield {"type": "error", "data": {"error": "RAG stream failed"}}
                    yield {"type": "done"}
                    return

            if final_state is not None:
                result = await self.rag_service.finalize(query=query, state=final_state)
                yield {
                    "type": "content_replace",
                    "data": {"text": result.content, "provisional": False},
                }
                yield {
                    "type": "metadata",
                    "data": {
                        **{
                            key: result.metadata[key]
                            for key in (
                                "documents_used",
                                "rejection_detected",
                                "rejection_reasoning",
                                "has_relevant_docs",
                            )
                            if key in result.metadata
                        },
                        "citations": [self._citation_dict(item) for item in result.citations],
                        "sources": [self._citation_dict(item) for item in result.citations],
                    },
                }
            else:
                if preview_started:
                    yield {"type": "content_replace", "data": {"text": "", "provisional": True}}
                yield {"type": "error", "data": {"error": "RAG stream failed"}}
            yield {"type": "done"}
        except Exception:
            logger.exception("RAG streaming failed")
            if preview_started:
                yield {"type": "content_replace", "data": {"text": "", "provisional": True}}
            yield {"type": "error", "data": {"error": "RAG stream failed"}}
            yield {"type": "done"}
        finally:
            await stream.aclose()

    @staticmethod
    def _validate_intent(classification: ClassificationResult) -> None:
        if classification.intent != Intent.RAG:
            raise ValueError(f"RAGHandler cannot handle intent: {classification.intent}")

    @staticmethod
    def _history_kwargs(context: dict[str, Any] | None) -> dict[str, Any]:
        """Forward bounded history while retaining compatibility with simple workflows."""
        history = (context or {}).get("conversation_history")
        return {"history": history} if history else {}

    @staticmethod
    def _status_event(stage: str, state: dict[str, Any], duration_ms: int) -> dict[str, Any]:
        """Translate one finished LangGraph node into a ``status`` SSE chunk.

        The payload drives the pipeline timeline in the chat UI and is persisted with the
        assistant message, so keep it small and JSON-serialisable.
        """
        iteration = (state.get("orchestrator_state") or {}).get("iteration_count", 0)
        metadata: dict[str, Any] = {"duration_ms": duration_ms, "iteration": iteration}

        if stage == "orchestrator":
            metadata["fallback"] = bool(state.get("should_fallback"))
            if state.get("fallback_reason"):
                metadata["fallback_reason"] = "rag_pipeline_fallback"
        elif stage == "retrieval":
            output = state.get("retrieval_agent_output", {})
            documents = output.get("reranked_docs") or output.get("retrieved_docs") or []
            metadata["docs_retrieved"] = len(documents)
            metadata["refined_queries"] = output.get("refined_queries", [])
        elif stage == "generation":
            metadata["response_length"] = len(state.get("generated_response", ""))
        elif stage == "quality":
            output = state.get("quality_agent_output", {})
            verification = output.get("verification") or {}
            if state.get("should_fallback"):
                decision = "fallback"
            elif state.get("routing_decision") == "regenerate":
                decision = "regenerate"
            else:
                decision = "pass"
            metadata["quality_score"] = output.get("quality_score", 0.0)
            metadata["should_regenerate"] = output.get("should_regenerate", False)
            metadata["verified"] = verification.get("is_verified") is True
            metadata["decision"] = decision
        return {"type": "status", "data": {"stage": stage, "metadata": metadata}}

    @staticmethod
    def _citation_dict(citation: Any) -> dict[str, Any]:
        return {
            "filename": citation.filename,
            "text": citation.text,
            "page": citation.page,
            "confidence": citation.confidence,
            "document_id": citation.document_id,
            "chunk_index": citation.chunk_index,
        }

    @staticmethod
    def _to_handler_result(result: RAGExecutionResult) -> HandlerResult:
        citations = [
            Citation(
                filename=item.filename,
                text=item.text,
                page=item.page,
                confidence=item.confidence,
                metadata={
                    "document_id": item.document_id,
                    "chunk_index": item.chunk_index,
                },
            )
            for item in result.citations
        ]
        return HandlerResult(content=result.content, citations=citations, metadata=result.metadata)

    def can_handle(self, classification: ClassificationResult) -> bool:
        return classification.intent == Intent.RAG

    def get_config(self) -> HandlerConfig:
        return self.config

    def get_name(self) -> str:
        return "RAGHandler"
