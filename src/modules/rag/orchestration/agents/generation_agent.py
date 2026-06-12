"""
GenerationAgent: LLM response generation with citations (4-agent architecture)

This agent generates the final response using retrieved context:
- Context building from retrieved documents
- LLM generation with proper citations
- Streaming support for real-time responses
- Response regeneration based on feedback

Compatible with 4-agent architecture:
    Input: RAGState (query, retrieval_agent_output)
    Process: Build context -> Generate response with citations
    Output: RAGState with generated_response

Example:
    agent = GenerationAgent(config=GenerationAgentConfig(), llm_client=llm)
    state = await agent.handle(state)
    response = state["generated_response"]
"""

import logging
from typing import List, Dict, Any, AsyncIterator, Optional
from datetime import datetime
import time

from src.shared.ports.llm import LLMPort
from src.modules.rag.orchestration.state.rag_state import (
    RAGState,
    AgentStatus,
    DocumentWithScore,
    GenerationAgentConfig,
    Citation,
    create_agent_result,
    mark_agent_start,
    update_state_with_agent_result,
    get_retrieval_docs
)
from src.modules.rag.domain.prompts.generation import (
    build_generation_prompt,
    build_regeneration_prompt,
)

logger = logging.getLogger(__name__)


class GenerationAgent:
    """
    Agent for LLM-based response generation.

    Responsibilities:
    - Build context from retrieved documents (retrieval_agent_output)
    - Generate LLM response with proper citations
    - Stream responses in real-time
    - Handle regeneration based on quality feedback
    - Format citations according to configuration

    Attributes:
        config: GenerationAgentConfig
        llm_client: LLM client for generation
    """

    def __init__(self, config: GenerationAgentConfig, llm_client: Optional[LLMPort] = None):
        """
        Initialize GenerationAgent.

        Args:
            config: GenerationAgent configuration
            llm_client: Optional LLM client for generation
        """
        self.config = config
        self.llm_client = llm_client

    @staticmethod
    def _messages_from_prompt(prompt: str) -> list[dict[str, str]]:
        """Convert the agent prompt into chat message format."""
        return [{"role": "user", "content": prompt}]

    async def _generate_text(
        self,
        prompt: str,
        *,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate text using the configured LLM client."""
        if self.llm_client is None:
            raise RuntimeError("GenerationAgent requires an LLMPort dependency")

        return await self.llm_client.generate(
            messages=self._messages_from_prompt(prompt),
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def _stream_text(
        self,
        prompt: str,
        *,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Stream text using the configured LLM client."""
        if self.llm_client is None:
            raise RuntimeError("GenerationAgent requires an LLMPort dependency")

        async for chunk in self.llm_client.stream(
            messages=self._messages_from_prompt(prompt),
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk

    async def handle(
        self,
        state: RAGState,
        context: Optional[Dict[str, Any]] = None
    ) -> RAGState:
        """
        Generate response (non-streaming).

        This is the main entry point compatible with 4-agent architecture.
        It retrieves documents from retrieval_agent_output and generates response.

        Args:
            state: Current RAGState with retrieval_agent_output
            context: Optional additional context

        Returns:
            Updated RAGState with generated_response
        """
        start_time = time.time()
        state = mark_agent_start(state, "GenerationAgent")

        try:
            query = state["query"]
            documents = get_retrieval_docs(state)

            logger.info(f"GenerationAgent starting: query='{query[:50]}...', docs={len(documents)}")

            # Build context from documents
            context_str = self._build_context(documents)

            # Build prompt
            prompt = self._build_prompt(query, context_str)

            # Generate response
            response = await self._generate_text(
                prompt=prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )

            # Extract citations
            citations = self._extract_citations(documents) if self.config.include_citations else []

            # Update state
            state["generated_response"] = response
            state["final_response"] = response
            state["final_citations"] = citations
            state["generation_metadata"] = {
                "model": self.config.model,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "context_size": len(context_str),
                "documents_used": len(documents),
                "generated_at": datetime.utcnow().isoformat()
            }

            execution_time = (time.time() - start_time) * 1000
            result = create_agent_result(
                agent_name="GenerationAgent",
                status=AgentStatus.COMPLETED,
                execution_time_ms=execution_time,
                metadata={
                    "response_length": len(response),
                    "citations_count": len(citations),
                    "documents_used": len(documents)
                }
            )

            logger.info(f"GenerationAgent completed in {execution_time:.0f}ms: {len(response)} chars")
            return update_state_with_agent_result(state, result)

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"GenerationAgent failed: {e}", exc_info=True)

            result = create_agent_result(
                agent_name="GenerationAgent",
                status=AgentStatus.FAILED,
                execution_time_ms=execution_time,
                error_message=str(e)
            )

            state = update_state_with_agent_result(state, result)
            state["generated_response"] = ""
            return state

    async def handle_stream(
        self,
        state: RAGState,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Generate response with streaming.

        Yields content chunks in real-time for better UX.

        Args:
            state: Current RAGState
            context: Optional additional context

        Yields:
            Streaming chunks with content and metadata
        """
        start_time = time.time()
        state = mark_agent_start(state, "GenerationAgent")

        try:
            query = state["query"]
            documents = get_retrieval_docs(state)

            logger.info(f"GenerationAgent streaming: docs={len(documents)}")

            # Build context and prompt
            context_str = self._build_context(documents)
            prompt = self._build_prompt(query, context_str)

            # Stream generation
            full_response = ""
            citations = self._extract_citations(documents) if self.config.include_citations else []

            async for chunk in self._stream_text(
                prompt=prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            ):
                full_response += chunk

                # Yield content chunk
                yield {
                    "type": "content",
                    "data": {
                        "text": chunk,
                        "done": False
                    }
                }

            # Update state
            state["generated_response"] = full_response
            state["final_response"] = full_response
            state["final_citations"] = citations
            state["generation_metadata"] = {
                "model": self.config.model,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "context_size": len(context_str),
                "documents_used": len(documents),
                "streaming": True,
                "generated_at": datetime.utcnow().isoformat()
            }

            # Yield final metadata
            yield {
                "type": "metadata",
                "data": {
                    "citations": [c.model_dump() for c in citations],
                    "documents_used": len(documents),
                    "response_length": len(full_response)
                }
            }

            execution_time = (time.time() - start_time) * 1000
            result = create_agent_result(
                agent_name="GenerationAgent",
                status=AgentStatus.COMPLETED,
                execution_time_ms=execution_time,
                metadata={
                    "response_length": len(full_response),
                    "citations_count": len(citations),
                    "streaming": True
                }
            )

            state = update_state_with_agent_result(state, result)

            logger.info(f"GenerationAgent streaming completed: {len(full_response)} chars")
            return

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"GenerationAgent streaming failed: {e}", exc_info=True)

            result = create_agent_result(
                agent_name="GenerationAgent",
                status=AgentStatus.FAILED,
                execution_time_ms=execution_time,
                error_message=str(e)
            )

            state = update_state_with_agent_result(state, result)

            # Yield error chunk
            yield {
                "type": "error",
                "data": {
                    "message": str(e)
                }
            }
            return

    def can_handle(self, state: RAGState) -> bool:
        """
        Check if generation agent can handle the current state.

        GenerationAgent requires retrieval_agent_output with documents.

        Args:
            state: Current RAGState

        Returns:
            True if state has retrieval_agent_output
        """
        return bool(
            state.get("retrieval_agent_output") and
            state["retrieval_agent_output"].get("reranked_docs") or
            state["retrieval_agent_output"].get("retrieved_docs")
        )

    # ==========================================================================
    # Context Building
    # ==========================================================================

    def _build_context(self, documents: List[DocumentWithScore]) -> str:
        """
        Build context string from retrieved documents.

        TODO: Enhance context building with:
        - Intelligent document selection
        - Context compression for long documents
        - Deduplication of similar content

        Args:
            documents: List of retrieved documents

        Returns:
            Formatted context string
        """
        if not documents:
            return "No relevant documents found."

        context_parts = []

        for idx, doc in enumerate(documents, 1):
            source = f"{doc.filename}"
            if doc.page_number:
                source += f", page {doc.page_number}"

            # Truncate very long documents
            content = doc.content
            if len(content) > 1000:
                content = content[:1000] + "..."

            context_parts.append(
                f"[Document {idx}] (Source: {source}, Relevance: {doc.score:.2f})\n{content}\n"
            )

        return "\n".join(context_parts)

    # ==========================================================================
    # Prompt Building
    # ==========================================================================

    def _build_prompt(self, query: str, context: str) -> str:
        """
        Build generation prompt with context and instructions.

        TODO: Customize prompts based on:
        - Query type (factual, analytical, creative)
        - Domain-specific requirements
        - User preferences

        Args:
            query: User query
            context: Retrieved context

        Returns:
            Formatted prompt
        """
        return build_generation_prompt(query=query, context=context)

    # ==========================================================================
    # Citation Extraction
    # ==========================================================================

    def _extract_citations(self, documents: List[DocumentWithScore]) -> List[Citation]:
        """
        Extract citations from retrieved documents.

        TODO: Enhance citation extraction with:
        - Smart citation placement
        - Page range extraction
        - Highlighted text snippets

        Args:
            documents: List of documents

        Returns:
            List of Citation objects
        """
        citations = []

        for idx, doc in enumerate(documents, 1):
            # Truncate citation text
            text = doc.content
            if len(text) > 200:
                text = text[:200] + "..."

            citation = Citation(
                filename=doc.filename,
                page_number=doc.page_number,
                text=text,
                doc_index=idx,
                score=doc.score
            )
            citations.append(citation)

        return citations

    # ==========================================================================
    # Regeneration (for QualityAgent feedback)
    # ==========================================================================

    async def regenerate_with_feedback(
        self,
        state: RAGState,
        feedback: str
    ) -> RAGState:
        """
        Regenerate response based on quality feedback.

        This is called by QualityAgent when regeneration is needed.

        TODO: Implement sophisticated regeneration with:
        - Specific issue addressing
        - Incremental improvement
        - Feedback learning

        Args:
            state: Current RAGState
            feedback: Quality feedback for improvement

        Returns:
            Updated RAGState with regenerated response
        """
        start_time = time.time()
        state = mark_agent_start(state, "GenerationAgent (regenerate)")

        try:
            query = state["query"]
            previous_response = state["generated_response"]
            documents = get_retrieval_docs(state)

            logger.info(f"Regenerating with feedback: {feedback[:100]}...")

            # Build context
            context_str = self._build_context(documents)

            # Build regeneration prompt
            prompt = self._build_regeneration_prompt(
                query=query,
                context=context_str,
                previous_response=previous_response,
                feedback=feedback
            )

            # Generate improved response
            response = await self._generate_text(
                prompt=prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )

            # Update state
            state["generated_response"] = response
            if state.get("generation_metadata"):
                state["generation_metadata"]["regenerated"] = True
                state["generation_metadata"]["regeneration_feedback"] = feedback

            execution_time = (time.time() - start_time) * 1000
            result = create_agent_result(
                agent_name="GenerationAgent (regenerate)",
                status=AgentStatus.COMPLETED,
                execution_time_ms=execution_time,
                metadata={
                    "regeneration": True,
                    "feedback": feedback,
                    "response_length": len(response)
                }
            )

            logger.info(f"Regeneration completed: {len(response)} chars")
            return update_state_with_agent_result(state, result)

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Regeneration failed: {e}", exc_info=True)

            result = create_agent_result(
                agent_name="GenerationAgent (regenerate)",
                status=AgentStatus.FAILED,
                execution_time_ms=execution_time,
                error_message=str(e)
            )

            return update_state_with_agent_result(state, result)

    def _build_regeneration_prompt(
        self,
        query: str,
        context: str,
        previous_response: str,
        feedback: str
    ) -> str:
        """
        Build prompt for regeneration with feedback.

        TODO: Improve regeneration prompting with:
        - Specific issue targeting
        - Progressive improvement hints
        - Quality metric feedback

        Args:
            query: Original query
            context: Retrieved context
            previous_response: Previous generated response
            feedback: Quality feedback

        Returns:
            Formatted regeneration prompt
        """
        return build_regeneration_prompt(
            query=query,
            context=context,
            previous_response=previous_response,
            feedback=feedback,
        )
