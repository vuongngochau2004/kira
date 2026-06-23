"""RAG pipeline application service."""

from typing import Any, AsyncIterator
from uuid import UUID

from src.modules.rag.application.dto import RAGCitation, RAGExecutionResult
from src.modules.rag.application.ports import RAGWorkflowPort
from src.modules.rag.domain.services.rag_domain_service import RAGService


class RAGPipelineService:
    """Application service that runs the RAG domain pipeline."""

    def __init__(self, pipeline: RAGWorkflowPort):
        """Initialize with a composed domain pipeline."""
        self.pipeline = pipeline

    @property
    def llm(self):
        """Return the pipeline LLM dependency when available."""
        return getattr(self.pipeline, "llm", None)

    async def run(
        self,
        query: str,
        user_id: str,
        conversation_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Run the RAG pipeline and return the final state."""
        return await self.pipeline.run(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
        )

    async def execute(
        self,
        query: str,
        user_id: str,
        conversation_id: UUID | None = None,
    ) -> RAGExecutionResult:
        """Run the workflow and return its stable application result."""
        state = await self.run(query=query, user_id=user_id, conversation_id=conversation_id)
        return await self.finalize(query=query, state=state)

    async def finalize(self, query: str, state: dict[str, Any]) -> RAGExecutionResult:
        """Apply RAG completion rules and hide workflow state from callers."""
        content = state.get("final_response") or state.get("generated_response") or ""
        raw_citations = state.get("final_citations") or []
        citations = [citation for item in raw_citations if (citation := self._citation_from(item))]

        metadata = dict(state.get("generation_metadata") or {})
        metadata.update(
            {
                "agent_results": [
                    item.model_dump() if hasattr(item, "model_dump") else item
                    for item in state.get("agent_results", [])
                ],
                "total_execution_time_ms": state.get("total_execution_time_ms", 0.0),
                "quality": state.get("quality_agent_output", {}),
            }
        )

        if not citations:
            metadata.update(
                {
                    "rejection_detected": True,
                    "rejection_reasoning": "generation_no_citations",
                    "has_relevant_docs": False,
                }
            )
            return RAGExecutionResult(content=content, metadata=metadata, rejected=True)

        evidence = self._build_evidence(state=state, citations=citations)
        relevance = await RAGService.evaluate_relevance(
            query=query,
            response=content,
            context=evidence,
            llm=self.llm,
        )
        rejected = not relevance.get("has_relevant_docs", False)
        metadata["relevance_context_chars"] = len(evidence)
        metadata["has_relevant_docs"] = not rejected
        if rejected:
            metadata.update(
                {
                    "rejection_detected": True,
                    "rejection_reasoning": relevance.get("reason") or content,
                    "relevance_filtering": {
                        "enabled": True,
                        "is_rejection": True,
                        "rejection_reason": relevance.get("reason") or "no_relevant_docs",
                        "structured": not relevance.get("fallback", False),
                    },
                }
            )
            citations = []

        return RAGExecutionResult(
            content=content,
            citations=citations,
            metadata=metadata,
            rejected=rejected,
        )

    async def run_stream(
        self,
        query: str,
        user_id: str,
        conversation_id: UUID | None = None,
    ) -> AsyncIterator[dict]:
        """Stream updates from the RAG pipeline."""
        async for event in self.pipeline.run_stream(
            query=query,
            user_id=user_id,
            conversation_id=conversation_id,
        ):
            yield event

    @staticmethod
    def _citation_from(value: Any) -> RAGCitation | None:
        """Normalize workflow citations into the public application DTO."""
        if hasattr(value, "model_dump"):
            value = value.model_dump()
        if not isinstance(value, dict):
            return None
        text = value.get("text") or ""
        if not text:
            return None
        return RAGCitation(
            filename=value.get("filename") or "",
            text=text,
            page=value.get("page_number") or value.get("page"),
            confidence=value.get("score") if value.get("score") is not None else 1.0,
            document_id=str(value["document_id"]) if value.get("document_id") else None,
            chunk_index=value.get("chunk_index"),
        )

    @staticmethod
    def _build_evidence(state: dict[str, Any], citations: list[RAGCitation]) -> str:
        """Build bounded evidence for relevance validation from retrieved chunks."""
        retrieval = state.get("retrieval_agent_output") or {}
        documents = retrieval.get("reranked_docs") or retrieval.get("retrieved_docs") or []
        parts: list[str] = []
        remaining = 20_000
        for index, document in enumerate(documents, start=1):
            if not isinstance(document, dict) or remaining <= 0:
                continue
            content = str(document.get("content") or "")
            if not content:
                continue
            content = content[: min(4_000, remaining)]
            source = document.get("filename") or f"Document {index}"
            part = f"[Document {index}] {source}\n{content}"
            parts.append(part)
            remaining -= len(part) + 2

        if parts:
            return "\n\n".join(parts)
        return "\n\n".join(
            f"[Document {index}] {citation.filename}\n{citation.text}"
            for index, citation in enumerate(citations, start=1)
        )


__all__ = ["RAGPipelineService"]
