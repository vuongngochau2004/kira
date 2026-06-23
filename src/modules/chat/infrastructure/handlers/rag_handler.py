"""Chat transport adapter for the RAG application use case."""

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
            )
            return self._to_handler_result(result)
        except Exception as exc:
            logger.exception("RAG execution failed")
            return HandlerResult(
                content="Có lỗi xảy ra khi xử lý câu hỏi.",
                citations=[],
                metadata={"handler": self.get_name()},
                status="error",
                error=str(exc),
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
        emitted_content = False
        try:
            async for event in self.rag_service.run_stream(
                query=query,
                user_id=str(user_id),
                conversation_id=(context or {}).get("conversation_id"),
            ):
                mode = event.get("mode")
                chunk = event.get("chunk")
                if mode == "messages":
                    text = self._message_text(chunk)
                    if text:
                        emitted_content = True
                        yield {"type": "content", "data": {"text": text}}
                elif mode == "updates" and isinstance(chunk, dict):
                    for stage, state in chunk.items():
                        if not isinstance(state, dict):
                            continue
                        final_state = state
                        yield self._status_event(stage, state)
                elif mode == "error":
                    yield {"type": "error", "data": {"error": str(chunk)}}

            if final_state is not None:
                result = await self.rag_service.finalize(query=query, state=final_state)
                if result.content and not emitted_content:
                    yield {"type": "content", "data": {"text": result.content}}
                yield {
                    "type": "metadata",
                    "data": {
                        **result.metadata,
                        "citations": [self._citation_dict(item) for item in result.citations],
                        "sources": [self._citation_dict(item) for item in result.citations],
                    },
                }
            yield {"type": "done"}
        except Exception as exc:
            logger.exception("RAG streaming failed")
            yield {"type": "error", "data": {"error": str(exc)}}
            yield {"type": "done"}

    @staticmethod
    def _validate_intent(classification: ClassificationResult) -> None:
        if classification.intent != Intent.RAG:
            raise ValueError(f"RAGHandler cannot handle intent: {classification.intent}")

    @staticmethod
    def _message_text(chunk: Any) -> str:
        if isinstance(chunk, tuple):
            chunk = chunk[0]
        content = getattr(chunk, "content", chunk)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                item if isinstance(item, str) else item.get("text", "")
                for item in content
                if isinstance(item, (str, dict))
            )
        return ""

    @staticmethod
    def _status_event(stage: str, state: dict[str, Any]) -> dict[str, Any]:
        if stage == "retrieval":
            output = state.get("retrieval_agent_output", {})
            documents = output.get("reranked_docs") or output.get("retrieved_docs") or []
            metadata = {"docs_retrieved": len(documents), "refined_queries": output.get("refined_queries", [])}
        elif stage == "quality":
            output = state.get("quality_agent_output", {})
            metadata = {"quality_score": output.get("quality_score", 0.0), "should_regenerate": output.get("should_regenerate", False)}
        else:
            metadata = {"response_length": len(state.get("generated_response", ""))} if stage == "generation" else {}
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
