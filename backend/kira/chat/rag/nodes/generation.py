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
import re
import time
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import Any

from kira.chat.rag.prompts.generation import (
    build_generation_prompt,
    build_regeneration_prompt,
)
from kira.chat.rag.state import (
    AgentStatus,
    Citation,
    DocumentWithScore,
    GenerationAgentConfig,
    RAGState,
    create_agent_result,
    get_retrieval_docs,
    mark_agent_start,
    update_state_with_agent_result,
)
from kira.config import settings
from kira.providers.llm.base import LLMPort

logger = logging.getLogger(__name__)

VIETNAMESE_STOPWORDS = {
    "anh",
    "bao",
    "bằng",
    "các",
    "căn",
    "cho",
    "có",
    "của",
    "đã",
    "được",
    "gì",
    "hay",
    "khi",
    "là",
    "nào",
    "những",
    "theo",
    "trong",
    "từ",
    "và",
    "vào",
    "về",
    "việc",
}

CONDITION_QUERY_MARKERS = (
    "điều kiện",
    "khi nào",
    "trường hợp",
    "yêu cầu",
    "tiêu chuẩn",
    "được phép",
    "áp dụng",
    "cần đáp ứng",
)

RESPONSIBILITY_QUERY_MARKERS = (
    "trách nhiệm",
    "ai chịu trách nhiệm",
    "đơn vị nào",
    "cơ quan nào",
    "phòng nào",
    "nhiệm vụ",
    "phụ trách",
    "chủ trì",
    "thực hiện",
)

PROCEDURE_QUERY_MARKERS = (
    "thủ tục",
    "quy trình",
    "các bước",
    "trình tự",
    "hồ sơ",
    "nộp",
    "xử lý",
    "thực hiện như thế nào",
)

SUPPORT_SENTENCE_MARKERS = (
    "bao gồm",
    "cụ thể",
    "đồng thời",
    "trường hợp",
    "nếu",
    "khi",
    "phải",
    "được",
    "không được",
    "trách nhiệm",
    "chủ trì",
    "phối hợp",
    "thực hiện",
    "hồ sơ",
    "bước",
    "quy trình",
    "thủ tục",
)


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

    def __init__(self, config: GenerationAgentConfig, llm_client: LLMPort | None = None):
        """
        Initialize GenerationAgent.

        Args:
            config: GenerationAgent configuration
            llm_client: Optional LLM client for generation
        """
        self.config = config
        self.llm_client = llm_client

    @staticmethod
    def _generation_query(state: RAGState) -> str:
        """Keep original wording while giving follow-ups a bounded search referent."""
        original = state["query"]
        resolved = state.get("retrieval_query") or original
        if resolved == original:
            return original
        return f"{original}\nContext for resolving references only: {resolved[:2000]}"

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

        stream = self.llm_client.stream(
            messages=self._messages_from_prompt(prompt),
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            async for chunk in stream:
                yield chunk
        finally:
            close = getattr(stream, "aclose", None)
            if close is not None:
                await close()

    async def generate_for_graph_stream(
        self,
        state: RAGState,
        on_token: Callable[[str], None],
        feedback: str | None = None,
    ) -> RAGState:
        """Stream one graph generation attempt and update the same workflow state."""
        start_time = time.time()
        agent_name = "GenerationAgent (regenerate)" if feedback is not None else "GenerationAgent"
        state = mark_agent_start(state, agent_name)
        query = self._generation_query(state)
        documents = get_retrieval_docs(state)
        context_str, compressed_contexts = self._build_context(query, documents)
        if feedback is None:
            prompt = self._build_prompt(query, context_str)
        else:
            prompt = self._build_regeneration_prompt(
                query=query,
                context=context_str,
                previous_response=state["generated_response"],
                feedback=feedback,
            )

        parts: list[str] = []
        async for chunk in self._stream_text(
            prompt=prompt,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        ):
            parts.append(chunk)
            on_token(chunk)

        response = "".join(parts).strip()
        state["generated_response"] = response
        state["final_response"] = response
        if feedback is None:
            state["final_citations"] = (
                self._extract_citations(documents) if self.config.include_citations else []
            )
        metadata = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "context_size": len(context_str),
            "compressed_contexts": compressed_contexts,
            "raw_context_size": sum(len(doc.content or "") for doc in documents),
            "documents_used": len(documents),
            "streaming": True,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        if feedback is not None:
            metadata.update({"regenerated": True, "regeneration_feedback": feedback})
        state["generation_metadata"] = metadata
        result = create_agent_result(
            agent_name=agent_name,
            status=AgentStatus.COMPLETED,
            execution_time_ms=(time.time() - start_time) * 1000,
            metadata={"response_length": len(response), "documents_used": len(documents)},
        )
        return update_state_with_agent_result(state, result)

    async def handle(self, state: RAGState, context: dict[str, Any] | None = None) -> RAGState:
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
            query = self._generation_query(state)
            documents = get_retrieval_docs(state)

            logger.info("Generation starting: query_chars={}, docs={}", len(query), len(documents))

            # Build compressed context from documents
            context_str, compressed_contexts = self._build_context(query, documents)

            # Build prompt
            prompt = self._build_prompt(query, context_str)

            # Generate response
            response = await self._generate_text(
                prompt=prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            # Use response directly as plain text (no JSON wrapping)
            answer_text = response.strip()

            # Extract citations from retrieved documents
            citations = self._extract_citations(documents) if self.config.include_citations else []

            # Update state
            state["generated_response"] = answer_text
            state["final_response"] = answer_text
            state["final_citations"] = citations
            state["generation_metadata"] = {
                "model": self.config.model,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "context_size": len(context_str),
                "compressed_contexts": compressed_contexts,
                "raw_context_size": sum(len(doc.content or "") for doc in documents),
                "documents_used": len(documents),
                "generated_at": datetime.now(UTC).isoformat(),
            }

            execution_time = (time.time() - start_time) * 1000
            result = create_agent_result(
                agent_name="GenerationAgent",
                status=AgentStatus.COMPLETED,
                execution_time_ms=execution_time,
                metadata={
                    "response_length": len(response),
                    "citations_count": len(citations),
                    "documents_used": len(documents),
                },
            )

            logger.info(
                f"GenerationAgent completed in {execution_time:.0f}ms: {len(response)} chars"
            )
            return update_state_with_agent_result(state, result)

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"GenerationAgent failed: {e}", exc_info=True)

            result = create_agent_result(
                agent_name="GenerationAgent",
                status=AgentStatus.FAILED,
                execution_time_ms=execution_time,
                error_message=str(e),
            )

            state = update_state_with_agent_result(state, result)
            state["generated_response"] = ""
            return state

    async def handle_stream(
        self, state: RAGState, context: dict[str, Any] | None = None
    ) -> AsyncIterator[dict[str, Any]]:
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
            query = self._generation_query(state)
            documents = get_retrieval_docs(state)

            logger.info(f"GenerationAgent streaming: docs={len(documents)}")

            # Build context and prompt
            context_str, compressed_contexts = self._build_context(query, documents)
            prompt = self._build_prompt(query, context_str)

            # Stream generation — yield each token chunk directly to the frontend
            full_response = ""

            async for chunk in self._stream_text(
                prompt=prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            ):
                full_response += chunk
                yield {"type": "content", "data": {"text": chunk, "done": False}}

            # Use full response directly as plain text (no JSON parsing)
            answer_text = full_response.strip()

            # Extract citations from retrieved documents
            citations = self._extract_citations(documents) if self.config.include_citations else []

            # Update state
            state["generated_response"] = answer_text
            state["final_response"] = answer_text
            state["final_citations"] = citations
            state["generation_metadata"] = {
                "model": self.config.model,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "context_size": len(context_str),
                "compressed_contexts": compressed_contexts,
                "raw_context_size": sum(len(doc.content or "") for doc in documents),
                "documents_used": len(documents),
                "streaming": True,
                "generated_at": datetime.now(UTC).isoformat(),
            }

            # Yield final metadata
            yield {
                "type": "metadata",
                "data": {
                    "citations": [c.model_dump() for c in citations],
                    "documents_used": len(documents),
                    "response_length": len(answer_text),
                },
            }

            execution_time = (time.time() - start_time) * 1000
            result = create_agent_result(
                agent_name="GenerationAgent",
                status=AgentStatus.COMPLETED,
                execution_time_ms=execution_time,
                metadata={
                    "response_length": len(answer_text),
                    "citations_count": len(citations),
                    "streaming": True,
                },
            )

            state = update_state_with_agent_result(state, result)

            logger.info(f"GenerationAgent streaming completed: {len(answer_text)} chars")
            return

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"GenerationAgent streaming failed: {e}", exc_info=True)

            result = create_agent_result(
                agent_name="GenerationAgent",
                status=AgentStatus.FAILED,
                execution_time_ms=execution_time,
                error_message=str(e),
            )

            state = update_state_with_agent_result(state, result)

            # Yield error chunk
            yield {"type": "error", "data": {"message": str(e)}}
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
            state.get("retrieval_agent_output")
            and state["retrieval_agent_output"].get("reranked_docs")
            or state["retrieval_agent_output"].get("retrieved_docs")
        )

    # ==========================================================================
    # Context Building
    # ==========================================================================

    def _build_context(
        self, query: str, documents: list[DocumentWithScore]
    ) -> tuple[str, list[str]]:
        """
        Build context string from retrieved documents.

        Args:
            query: User query used to select relevant sentences
            documents: List of retrieved documents

        Returns:
            Formatted context string and plain compressed contexts
        """
        if not documents:
            return "No relevant documents found.", []

        context_parts = []
        compressed_contexts: list[str] = []
        total_chars = 0

        for idx, doc in enumerate(documents, 1):
            if total_chars >= settings.context_max_total_chars:
                break

            source = ""
            if doc.filename and doc.filename != "Unknown":
                source = f" {doc.filename}"
                if doc.page_number:
                    source += f", page {doc.page_number}"

            content = self._compress_content(query, doc.content)
            remaining = settings.context_max_total_chars - total_chars
            if len(content) > remaining:
                content = content[:remaining].rstrip() + "..."

            if source:
                context_parts.append(f"Document {idx}:{source}\n{content}\n")
            else:
                context_parts.append(f"Document {idx}:\n{content}\n")

            compressed_contexts.append(content)
            total_chars += len(content)

        return "\n".join(context_parts), compressed_contexts

    def _compress_content(self, query: str, content: str) -> str:
        """Keep the sentences most likely to answer the query."""
        text = (content or "").strip()
        if not text or not settings.context_compression_enabled:
            return self._truncate_context(text)

        sentences = self._split_sentences(text)
        if not sentences:
            return self._truncate_context(text)

        profile = self._query_profile(query)
        query_terms = self._query_terms(query)
        scored = [
            (self._sentence_score(sentence, query_terms, profile), index)
            for index, sentence in enumerate(sentences)
        ]
        positive = [(score, index) for score, index in scored if score > 0]
        positive.sort(key=lambda item: (-item[0], item[1]))

        selected_indices: set[int] = set()
        max_sentences = self._max_sentences_for_profile(profile)
        neighbor_radius = 2 if profile in {"condition", "responsibility", "procedure"} else 1

        for _, index in positive:
            for candidate in range(index - neighbor_radius, index + neighbor_radius + 1):
                if 0 <= candidate < len(sentences):
                    selected_indices.add(candidate)
            self._include_support_sentences(sentences, selected_indices, index, profile)
            if len(selected_indices) >= max_sentences:
                break

        selected = [sentences[index] for index in sorted(selected_indices)]
        if not selected:
            selected = sentences[: min(max(2, max_sentences // 2), len(sentences))]
        else:
            selected = selected[:max_sentences]

        return self._truncate_context(" ".join(selected))

    def _truncate_context(self, text: str) -> str:
        """Apply the per-document context budget."""
        if len(text) <= settings.context_max_chars_per_doc:
            return text
        return text[: settings.context_max_chars_per_doc].rstrip() + "..."

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split Vietnamese administrative text into sentence-like units."""
        normalized = re.sub(r"\s+", " ", text).strip()
        parts = re.split(r"(?<=[.!?;:])\s+|\n+", normalized)
        return [part.strip() for part in parts if part.strip()]

    @staticmethod
    def _query_terms(query: str) -> set[str]:
        """Extract useful lexical terms from the query."""
        tokens = re.findall(r"[\wÀ-ỹ/.-]+", query.lower())
        return {token for token in tokens if len(token) >= 3 and token not in VIETNAMESE_STOPWORDS}

    @staticmethod
    def _query_profile(query: str) -> str:
        """Classify the query shape for context compression."""
        lowered = query.lower()
        if any(marker in lowered for marker in PROCEDURE_QUERY_MARKERS):
            return "procedure"
        if any(marker in lowered for marker in RESPONSIBILITY_QUERY_MARKERS):
            return "responsibility"
        if any(marker in lowered for marker in CONDITION_QUERY_MARKERS):
            return "condition"
        return "default"

    @staticmethod
    def _max_sentences_for_profile(profile: str) -> int:
        """Allow answer-bearing query types to keep more local context."""
        base = settings.context_max_sentences_per_doc
        if profile in {"condition", "responsibility", "procedure"}:
            return min(max(base + 2, 6), 8)
        return base

    @staticmethod
    def _include_support_sentences(
        sentences: list[str],
        selected_indices: set[int],
        anchor_index: int,
        profile: str,
    ) -> None:
        """Keep adjacent clauses that often contain conditions, owners, or steps."""
        if profile not in {"condition", "responsibility", "procedure"}:
            return

        for candidate in (anchor_index - 2, anchor_index + 2):
            if not 0 <= candidate < len(sentences):
                continue
            lowered = sentences[candidate].lower()
            if any(marker in lowered for marker in SUPPORT_SENTENCE_MARKERS):
                selected_indices.add(candidate)

    @staticmethod
    def _sentence_score(sentence: str, query_terms: set[str], profile: str = "default") -> float:
        """Score how directly a sentence supports the query."""
        lowered = sentence.lower()
        score = sum(1.0 for term in query_terms if term in lowered)
        if re.search(r"\d{1,4}[/.-]\d{1,4}|qđ|tt-|ngày|tháng|năm|điều|khoản", lowered):
            score += 0.5
        if any(marker in lowered for marker in ("trách nhiệm", "căn cứ", "quy định", "hiệu lực")):
            score += 0.5
        if profile == "condition" and any(
            marker in lowered for marker in ("điều kiện", "trường hợp", "nếu", "khi", "phải")
        ):
            score += 1.0
        if profile == "responsibility" and any(
            marker in lowered
            for marker in ("trách nhiệm", "chủ trì", "phối hợp", "thực hiện", "phụ trách")
        ):
            score += 1.0
        if profile == "procedure" and any(
            marker in lowered for marker in ("thủ tục", "quy trình", "bước", "hồ sơ", "nộp")
        ):
            score += 1.0
        return score

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

    def _extract_citations(self, documents: list[DocumentWithScore]) -> list[Citation]:
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
        snippet_length = max(settings.snippet_length, 200)

        for idx, doc in enumerate(documents, 1):
            # Keep source panel snippets readable while still bounded for payload size.
            text = doc.content
            if len(text) > snippet_length:
                text = text[:snippet_length].rstrip() + "..."

            citation = Citation(
                filename=doc.filename,
                page_number=doc.page_number,
                text=text,
                doc_index=idx,
                score=doc.score,
                document_id=str(doc.doc_id) if doc.doc_id else None,
            )
            citations.append(citation)

        return citations

    # ==========================================================================
    # Regeneration (for QualityAgent feedback)
    # ==========================================================================

    async def regenerate_with_feedback(self, state: RAGState, feedback: str) -> RAGState:
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
            query = self._generation_query(state)
            previous_response = state["generated_response"]
            documents = get_retrieval_docs(state)

            logger.info(f"Regenerating with feedback: {feedback[:100]}...")

            # Build compressed context
            context_str, compressed_contexts = self._build_context(query, documents)

            # Build regeneration prompt
            prompt = self._build_regeneration_prompt(
                query=query,
                context=context_str,
                previous_response=previous_response,
                feedback=feedback,
            )

            # Generate improved response
            response = await self._generate_text(
                prompt=prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            # Update state
            state["generated_response"] = response.strip()
            state["final_response"] = state["generated_response"]
            state["generation_metadata"].update(
                {
                    "regenerated": True,
                    "regeneration_feedback": feedback,
                    "compressed_contexts": compressed_contexts,
                    "context_size": len(context_str),
                }
            )

            execution_time = (time.time() - start_time) * 1000
            result = create_agent_result(
                agent_name="GenerationAgent (regenerate)",
                status=AgentStatus.COMPLETED,
                execution_time_ms=execution_time,
                metadata={
                    "regeneration": True,
                    "feedback": feedback,
                    "response_length": len(response),
                },
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
                error_message=str(e),
            )

            return update_state_with_agent_result(state, result)

    def _build_regeneration_prompt(
        self, query: str, context: str, previous_response: str, feedback: str
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
