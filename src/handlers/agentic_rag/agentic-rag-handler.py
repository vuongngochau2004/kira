"""
AgenticRAGHandler: Integration with existing K.I.R.A handlers

This module provides the integration layer for Agentic RAG with the existing
K.I.R.A system using the handler pattern and adapter pattern.
"""

import logging
from typing import Dict, Any, AsyncIterator, Optional
from uuid import UUID, uuid4
from datetime import datetime

from src.shared.kernel.interfaces.handlers import QueryHandlerBase, HandlerResult, HandlerConfig
from src.shared.kernel.interfaces.classification import ClassificationResult, Intent
from agents.llm import LLMClient
from models.agentic_rag_state import (
    RAGState,
    AgenticRAGConfig,
    create_initial_state,
    Citation
)
from graphs.agentic_rag_graph import create_agentic_rag_graph
from models.chat import ChatResponse, Citation as ResponseCitation

logger = logging.getLogger(__name__)


class AgenticRAGHandler(QueryHandlerBase):
    """
    Handler for Agentic RAG pipeline.

    This handler integrates the LangGraph-based Agentic RAG system
    with the existing K.I.R.A handler architecture.

    Responsibilities:
    - Execute Agentic RAG pipeline
    - Stream responses
    - Convert RAGState to HandlerResult
    - Provide backward compatibility
    """

    def __init__(self, config: HandlerConfig, agentic_config: AgenticRAGConfig, llm_client: LLMClient):
        """
        Initialize AgenticRAGHandler.

        Args:
            config: Handler configuration
            agentic_config: Agentic RAG configuration
            llm_client: LLM client instance
        """
        super().__init__(config)
        self.agentic_config = agentic_config
        self.llm_client = llm_client
        self.graph = None  # Will be created on first use

    async def handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: Dict[str, Any] | None = None
    ) -> HandlerResult:
        """
        Handle query using Agentic RAG pipeline (non-streaming).

        Args:
            query: User's query
            user_id: User ID
            classification: Classification result
            context: Optional context

        Returns:
            HandlerResult with response and metadata
        """
        start_time = datetime.utcnow()

        try:
            # Ensure graph is initialized
            if self.graph is None:
                self.graph = create_agentic_rag_graph(
                    config=self.agentic_config,
                    llm_client=self.llm_client
                )

            # Execute pipeline
            state = await self.graph.execute(
                query=query,
                user_id=str(user_id),
                conversation_id=context.get("conversation_id") if context else None
            )

            # Check if fallback occurred
            if state.get("should_fallback"):
                logger.warning(f"Agentic RAG fell back: {state.get('fallback_reason')}")
                # Would fall back to simple RAG here
                return await self._fallback_handle(query, user_id, classification, context)

            # Convert state to HandlerResult
            return self._state_to_handler_result(state, query, user_id, classification)

        except Exception as e:
            logger.error(f"Agentic RAG handler failed: {e}", exc_info=True)

            # Fallback to simple RAG
            return await self._fallback_handle(query, user_id, classification, context)

    async def handle_stream(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: Dict[str, Any] | None = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Handle query with streaming response.

        Args:
            query: User's query
            user_id: User ID
            classification: Classification result
            context: Optional context

        Yields:
            Streaming chunks
        """
        try:
            # Ensure graph is initialized
            if self.graph is None:
                self.graph = create_agentic_rag_graph(
                    config=self.agentic_config,
                    llm_client=self.llm_client
                )

            # Yield routing info
            yield {
                "type": "routing",
                "data": {
                    "handler": "AgenticRAGHandler",
                    "intent": classification.intent.value,
                    "confidence": classification.confidence,
                    "pipeline": "agentic_rag"
                }
            }

            # Stream pipeline execution
            async for chunk in self.graph.execute_stream(
                query=query,
                user_id=str(user_id),
                conversation_id=context.get("conversation_id") if context else None
            ):
                yield chunk

            # Yield final metadata
            yield {
                "type": "metadata",
                "data": {
                    "status": "success",
                    "handler": "AgenticRAGHandler"
                }
            }

        except Exception as e:
            logger.error(f"Agentic RAG streaming failed: {e}", exc_info=True)

            # Yield error
            yield {
                "type": "error",
                "data": {
                    "message": str(e),
                    "handler": "AgenticRAGHandler"
                }
            }

    def can_handle(self, classification: ClassificationResult) -> bool:
        """
        Check if this handler can handle the classification.

        Args:
            classification: Classification result

        Returns:
            True if handler can handle this intent
        """
        return classification.is_rag_intent()

    def get_config(self) -> HandlerConfig:
        """Get handler configuration"""
        return self._config

    def get_name(self) -> str:
        """Get handler name"""
        return "AgenticRAGHandler"

    def _state_to_handler_result(
        self,
        state: RAGState,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult
    ) -> HandlerResult:
        """
        Convert RAGState to HandlerResult.

        Args:
            state: Final RAGState
            query: Original query
            user_id: User ID
            classification: Classification result

        Returns:
            HandlerResult
        """
        # Extract response
        response_text = state.get("final_response") or state.get("generated_response", "")

        # Convert citations
        citations = [
            ResponseCitation(
                filename=cit.filename,
                page_number=cit.page_number,
                text=cit.text,
                doc_index=cit.doc_index,
                score=cit.score
            )
            for cit in state.get("final_citations", [])
        ]

        # Extract agent results
        agent_results = state.get("agent_results", [])

        # Build metadata
        metadata = {
            "handler": "AgenticRAGHandler",
            "intent": classification.intent.value,
            "confidence": classification.confidence,
            "pipeline": "agentic_rag",
            "total_execution_time_ms": state.get("total_execution_time_ms", 0),
            "agents_executed": len(agent_results),
            "agent_results": [
                {
                    "agent": r.agent_name,
                    "status": r.status.value,
                    "execution_time_ms": r.execution_time_ms
                }
                for r in agent_results
            ],
            "retrieval_metadata": state.get("retrieval_metadata"),
            "critique_result": state.get("critique_result"),
            "verification_result": state.get("verification_result")
        }

        return HandlerResult(
            content=response_text,
            citations=citations,
            metadata=metadata
        )

    async def _fallback_handle(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: Dict[str, Any] | None
    ) -> HandlerResult:
        """
        Fallback to simple RAG if Agentic RAG fails.

        Args:
            query: User's query
            user_id: User ID
            classification: Classification result
            context: Optional context

        Returns:
            HandlerResult from fallback
        """
        logger.info("Falling back to simple RAG")

        # Import simple RAG handler
        from handlers.rag import RAGHandler

        # Create simple RAG handler
        rag_handler = RAGHandler(config=self._config)

        # Execute simple RAG
        return await rag_handler.handle(query, user_id, classification, context)


# ============================================================================
# Handler Adapter
# ============================================================================

class AgenticRAGHandlerAdapter:
    """
    Adapter for integrating AgenticRAGHandler with existing router system.

    This provides backward compatibility with the legacy router pattern
    while using the new agentic architecture.
    """

    def __init__(
        self,
        agentic_config: AgenticRAGConfig,
        llm_client: LLMClient,
        base_handler_config: HandlerConfig | None = None
    ):
        """
        Initialize adapter.

        Args:
            agentic_config: Agentic RAG configuration
            llm_client: LLM client
            base_handler_config: Base handler configuration
        """
        self.agentic_config = agentic_config
        self.llm_client = llm_client
        self.base_config = base_handler_config or HandlerConfig()
        self.handler = None  # Created on first use

    def get_handler(self) -> AgenticRAGHandler:
        """
        Get or create AgenticRAGHandler instance.

        Returns:
            AgenticRAGHandler instance
        """
        if self.handler is None:
            self.handler = AgenticRAGHandler(
                config=self.base_config,
                agentic_config=self.agentic_config,
                llm_client=self.llm_client
            )
        return self.handler

    async def execute(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: Dict[str, Any] | None = None
    ) -> HandlerResult:
        """
        Execute Agentic RAG pipeline.

        Args:
            query: User's query
            user_id: User ID
            classification: Classification result
            context: Optional context

        Returns:
            HandlerResult
        """
        handler = self.get_handler()
        return await handler.handle(query, user_id, classification, context)

    async def execute_stream(
        self,
        query: str,
        user_id: str | UUID,
        classification: ClassificationResult,
        context: Dict[str, Any] | None = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute Agentic RAG with streaming.

        Args:
            query: User's query
            user_id: User ID
            classification: Classification result
            context: Optional context

        Yields:
            Streaming chunks
        """
        handler = self.get_handler()
        async for chunk in handler.handle_stream(query, user_id, classification, context):
            yield chunk


# ============================================================================
# Factory Functions
# ============================================================================

def create_agentic_rag_handler(
    llm_client: LLMClient,
    agentic_config: AgenticRAGConfig | None = None,
    base_config: HandlerConfig | None = None
) -> AgenticRAGHandler:
    """
    Factory function to create AgenticRAGHandler.

    Args:
        llm_client: LLM client instance
        agentic_config: Agentic RAG configuration (optional, uses defaults)
        base_config: Base handler configuration (optional)

    Returns:
        Configured AgenticRAGHandler
    """
    if agentic_config is None:
        agentic_config = AgenticRAGConfig()

    if base_config is None:
        base_config = HandlerConfig()

    return AgenticRAGHandler(
        config=base_config,
        agentic_config=agentic_config,
        llm_client=llm_client
    )


def create_agentic_rag_adapter(
    llm_client: LLMClient,
    agentic_config: AgenticRAGConfig | None = None
) -> AgenticRAGHandlerAdapter:
    """
    Factory function to create AgenticRAGHandlerAdapter.

    Args:
        llm_client: LLM client instance
        agentic_config: Agentic RAG configuration (optional)

    Returns:
        Configured AgenticRAGHandlerAdapter
    """
    if agentic_config is None:
        agentic_config = AgenticRAGConfig()

    return AgenticRAGHandlerAdapter(
        agentic_config=agentic_config,
        llm_client=llm_client
    )
