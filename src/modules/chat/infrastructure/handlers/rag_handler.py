"""RAG Handler using LangGraph-based multi-agent pipeline.

Replaces traditional OrchestratorAgent with LangGraph StateGraph architecture.
"""

from loguru import logger
from typing import AsyncIterator, Dict, Any, Optional
from uuid import UUID

from src.shared.ports.handlers import QueryHandlerBase, HandlerResult, HandlerConfig, Citation
from src.shared.ports.classification import ClassificationResult, Intent
from src.modules.rag.orchestration.state.rag_state import Citation as StateCitation
from src.modules.rag.application import RAGPipelineService
from src.modules.rag.composition import create_default_rag_pipeline_service
from src.modules.rag.domain.services.rag_domain_service import RAGService


class RAGHandler(QueryHandlerBase):
    """
    RAG handler using LangGraph multi-agent pipeline.
    
    Architecture:
        Entry → Orchestrator → Retrieval → Generation → Quality
                                              ↓
                                      [Conditional Edge]
                                              ↓
                                 [Regenerate] or [END]
    """

    def __init__(
        self,
        config: Optional[HandlerConfig] = None,
        rag_service: RAGPipelineService | None = None,
    ):
        """
        Initialize LangGraph RAG handler.

        Args:
            config: Optional handler configuration
        """
        self.config = config or HandlerConfig()
        self.rag_service = rag_service or create_default_rag_pipeline_service()

        logger.info("✅ RAGHandler initialized with LangGraph pipeline")

    @staticmethod
    def _extract_message_text(message_chunk: Any) -> str:
        """Extract text from a LangGraph messages stream chunk."""
        content = getattr(message_chunk, "content", message_chunk)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("text") or item.get("content") or "")
            return "".join(parts)
        return ""

    @staticmethod
    def _citation_to_dict(citation: Any) -> dict[str, Any]:
        """Convert citation models from the RAG state to API-safe dicts."""
        if isinstance(citation, dict):
            return {
                "filename": citation.get("filename", ""),
                "text": citation.get("text", ""),
                "page": citation.get("page_number") or citation.get("page"),
                "confidence": citation.get("score")
                if citation.get("score") is not None
                else citation.get("confidence", 1.0),
                "document_id": citation.get("document_id"),
            }
        if isinstance(citation, StateCitation):
            return {
                "filename": citation.filename,
                "text": citation.text,
                "page": citation.page_number,
                "confidence": citation.score if citation.score is not None else 1.0,
                "document_id": str(citation.document_id) if getattr(citation, "document_id", None) else None,
            }
        if isinstance(citation, Citation):
            return {
                "filename": citation.filename,
                "text": citation.text,
                "page": citation.page_number,
                "confidence": citation.score if citation.score is not None else 1.0,
                "document_id": citation.document_id,
            }
        return {}

    @classmethod
    def _build_relevance_context(cls, citations: list[Any]) -> str:
        """Build compact context text for structured relevance evaluation."""
        parts: list[str] = []
        for idx, citation in enumerate(citations, start=1):
            citation_dict = cls._citation_to_dict(citation)
            text = citation_dict.get("text", "")
            filename = citation_dict.get("filename", f"Document {idx}")
            if text:
                parts.append(f"[Document {idx}] {filename}\n{text}")
        return "\n\n".join(parts)

    @classmethod
    def _build_status_chunk(cls, node_name: str, state_update: dict[str, Any]) -> dict[str, Any]:
        """Create a compact status chunk from a LangGraph node update."""
        metadata: dict[str, Any] = {}

        if node_name == "retrieval":
            retrieval_output = state_update.get("retrieval_agent_output", {})
            docs = retrieval_output.get("reranked_docs") or retrieval_output.get("retrieved_docs") or []
            metadata = {
                "docs_retrieved": len(docs),
                "refined_queries": retrieval_output.get("refined_queries", []),
            }
        elif node_name == "generation":
            metadata = {
                "response_length": len(state_update.get("generated_response", "")),
                "citations_count": len(state_update.get("final_citations", [])),
            }
        elif node_name == "quality":
            quality_output = state_update.get("quality_agent_output", {})
            metadata = {
                "quality_score": quality_output.get("quality_score", 0.0),
                "should_regenerate": quality_output.get("should_regenerate", False),
            }
        elif node_name == "orchestrator":
            metadata = {
                "routing_decision": state_update.get("routing_decision"),
                "should_fallback": state_update.get("should_fallback", False),
            }

        return {
            "type": "status",
            "data": {
                "stage": node_name,
                "metadata": metadata,
            },
        }

    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: Optional[Dict[str, Any]] = None
    ) -> HandlerResult:
        """
        Handle RAG query using LangGraph pipeline.

        Args:
            query: User's query
            user_id: User ID
            classification: Query classification result
            context: Optional additional context

        Returns:
            HandlerResult with response and citations
        """
        logger.info(
            f"🚀 <yellow>[RAG FLOW]</yellow> Starting RAG handler (LangGraph). "
            f"Query: \"{query[:50] + '...' if len(query) > 50 else query}\", user_id='{user_id}'"
        )

        if classification.intent != Intent.RAG:
            raise ValueError(f"RAGHandler cannot handle intent: {classification.intent}")

        try:
            # Run LangGraph pipeline
            state = await self.rag_service.run(
                query=query,
                user_id=str(user_id),
                conversation_id=context.get("conversation_id") if context else None
            )

            # Extract results from state
            final_response = state.get("final_response", "")
            final_citations = state.get("final_citations", [])
            metadata = state.get("generation_metadata", {})

            # Add LangGraph metadata
            metadata["langgraph"] = True
            metadata["agent_results"] = state.get("agent_results", [])
            metadata["total_execution_time_ms"] = state.get("total_execution_time_ms", 0.0)

            # Short-circuit: if GenerationAgent already cleared citations (has_citations=false),
            # treat as rejection immediately — calling evaluate_relevance with empty context
            # would give unreliable results and waste an LLM call.
            if not final_citations:
                is_rejection = True
                relevance = {"has_relevant_docs": False, "reason": "generation_no_citations", "fallback": False}
            else:
                relevance = await RAGService.evaluate_relevance(
                    query=query,
                    response=final_response,
                    context=self._build_relevance_context(final_citations),
                    llm=self.rag_service.llm,
                )
                is_rejection = not relevance.get("has_relevant_docs", False)

            # Convert citations to expected format
            citations = []
            if is_rejection:
                metadata["rejection_detected"] = True
                metadata["rejection_reasoning"] = relevance.get("reason") or final_response
                metadata["relevance_filtering"] = {
                    "enabled": True,
                    "is_rejection": True,
                    "rejection_reason": relevance.get("reason") or "no_relevant_docs",
                    "structured": not relevance.get("fallback", False),
                }
                metadata["has_relevant_docs"] = False
            else:
                for citation in final_citations:
                    if isinstance(citation, dict):
                        citations.append(Citation(
                            filename=citation.get("filename", ""),
                            page=citation.get("page_number"),
                            text=citation.get("text", ""),
                            confidence=citation.get("score") if citation.get("score") is not None else 1.0
                        ))
                    elif isinstance(citation, StateCitation):
                        citations.append(Citation(
                            filename=citation.filename,
                            page=citation.page_number,
                            text=citation.text,
                            confidence=citation.score if citation.score is not None else 1.0
                        ))
                    elif isinstance(citation, Citation):
                        citations.append(citation)

            logger.info(
                f"✅ <green>[RAG FLOW COMPLETED]</green> RAG completed. "
                f"Citations: {len(citations)}, Latency: <yellow>{metadata['total_execution_time_ms']:.0f}ms</yellow>"
            )

            return HandlerResult(
                content=final_response,
                citations=citations,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"❌ <red>[RAG FLOW ERROR]</red> RAGHandler failed: {e}", exc_info=True)

            # Return error result
            return HandlerResult(
                content=f"Error processing query: {str(e)}",
                citations=[],
                metadata={"error": str(e), "langgraph": True},
                status="error",
                error=str(e)
            )

    async def handle_stream(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Handle RAG query with streaming using LangGraph pipeline.

        Args:
            query: User's query
            user_id: User ID
            classification: Query classification result
            context: Optional additional context

        Yields:
            Streaming chunks from LangGraph execution
        """
        logger.info(
            f"🚀 <yellow>[RAG STREAM FLOW]</yellow> Starting RAG streaming handler (LangGraph). "
            f"Query: \"{query[:50] + '...' if len(query) > 50 else query}\", user_id='{user_id}'"
        )

        if classification.intent != Intent.RAG:
            yield {
                "type": "metadata",
                "data": {
                    "status": "error",
                    "error": f"RAGHandler cannot handle intent: {classification.intent}"
                }
            }
            return

        try:
            # Yield routing chunk
            yield {
                "type": "routing",
                "data": {
                    "router": "LangGraphRAGPipeline",
                    "intent": classification.intent.value,
                    "confidence": classification.confidence
                }
            }

            final_state: dict[str, Any] | None = None
            emitted_message_tokens = False
            emitted_generation_snapshot = False

            # Stream LangGraph pipeline
            async for event in self.rag_service.run_stream(
                query=query,
                user_id=str(user_id),
                conversation_id=context.get("conversation_id") if context else None
            ):
                mode = event.get("mode") if isinstance(event, dict) else None
                chunk = event.get("chunk") if isinstance(event, dict) else event

                if mode == "messages":
                    # Stream each token directly — LLM now outputs plain text (no JSON wrapper)
                    message_chunk = chunk[0] if isinstance(chunk, tuple) else chunk
                    text = self._extract_message_text(message_chunk)
                    if text:
                        emitted_message_tokens = True
                        yield {
                            "type": "content",
                            "data": {"text": text},
                        }

                elif mode == "updates" and isinstance(chunk, dict):
                    for node_name, state_update in chunk.items():
                        if not isinstance(state_update, dict):
                            continue

                        final_state = state_update
                        yield self._build_status_chunk(node_name, state_update)

                        if node_name == "generation" and not emitted_message_tokens:
                            text = state_update.get("generated_response") or state_update.get("final_response") or ""
                            if text and not emitted_generation_snapshot:
                                emitted_generation_snapshot = True
                                yield {
                                    "type": "content",
                                    "data": {"text": text},
                                }

                elif mode == "error":
                    error_message = chunk.get("error", "LangGraph streaming failed") if isinstance(chunk, dict) else str(chunk)
                    yield {
                        "type": "error",
                        "data": {"error": error_message},
                    }

            if final_state:
                final_response = final_state.get("final_response") or final_state.get("generated_response") or ""
                if final_response and not emitted_message_tokens and not emitted_generation_snapshot:
                    yield {
                        "type": "content",
                        "data": {"text": final_response},
                    }

                final_citations = final_state.get("final_citations", [])

                # Short-circuit: if GenerationAgent already cleared citations (has_citations=false),
                # treat as rejection immediately — calling evaluate_relevance with empty context
                # would give unreliable results and waste an LLM call.
                if not final_citations:
                    is_rejection = True
                    relevance = {"has_relevant_docs": False, "reason": "generation_no_citations", "fallback": False}
                else:
                    relevance = await RAGService.evaluate_relevance(
                        query=query,
                        response=final_response,
                        context=self._build_relevance_context(final_citations),
                        llm=self.rag_service.llm,
                    )
                    is_rejection = not relevance.get("has_relevant_docs", False)

                citations = []
                if not is_rejection:
                    citations = [
                        citation
                        for citation in (
                            self._citation_to_dict(citation)
                            for citation in final_citations
                        )
                        if citation
                    ]

                metadata_payload = {
                    "langgraph": True,
                    "stream_modes": ["updates", "messages"],
                    "citations": citations,
                    "sources": citations,
                    "generation_metadata": final_state.get("generation_metadata", {}),
                    "quality": final_state.get("quality_agent_output", {}),
                    "total_execution_time_ms": final_state.get("total_execution_time_ms", 0.0),
                }

                if is_rejection:
                    metadata_payload["rejection_detected"] = True
                    metadata_payload["rejection_reasoning"] = relevance.get("reason") or final_response
                    metadata_payload["relevance_filtering"] = {
                        "enabled": True,
                        "is_rejection": True,
                        "rejection_reason": relevance.get("reason") or "no_relevant_docs",
                        "structured": not relevance.get("fallback", False),
                    }
                    metadata_payload["has_relevant_docs"] = False

                yield {
                    "type": "metadata",
                    "data": metadata_payload,
                }

            # Yield completion
            yield {"type": "done"}

        except Exception as e:
            logger.error(f"❌ <red>[RAG STREAM FLOW ERROR]</red> RAGHandler streaming failed: {e}", exc_info=True)
            yield {"type": "error", "data": {"error": str(e)}}
            yield {"type": "done"}

    def can_handle(self, classification: ClassificationResult) -> bool:
        """
        Check if handler can handle this classification.

        Args:
            classification: Query classification result

        Returns:
            True if handler can handle RAG intent
        """
        return classification.intent == Intent.RAG

    def get_config(self) -> HandlerConfig:
        """Get handler configuration."""
        return self.config

    def get_name(self) -> str:
        """Get handler name."""
        return "RAGHandler"
