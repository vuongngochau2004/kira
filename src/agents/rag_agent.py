"""Agentic RAG with self-evaluation and iterative retrieval."""

import asyncio
import logging
from uuid import UUID
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

# Retrieval Configuration
DEFAULT_MAX_ITERATIONS = 3
DEFAULT_RETRIEVAL_K = 5

# Query Rewriting Configuration
MAX_HISTORY_MESSAGES = 3  # Maximum number of recent messages to use for context
MAX_CONTEXT_CHARS = 8000  # Maximum character count for conversation context
MAX_QUERY_REWRITE_LENGTH = 500  # Maximum length for rewritten query

# Citation Configuration
DEFAULT_MAX_CITATIONS = 10  # Default maximum citations to extract

# Legal Terms for Hybrid Search
SPECIFIC_TERMS = ["điều khoản", "khoản", "điều", "nghị định", "thông tư", "luật"]

from src.agents.llm import chat_async, chat_async_stream
from src.agents.llm_post_process import stream_with_thinking_separation
from src.agents.prompts import ANSWER_GENERATOR_PROMPT, CITATION_AWARE_SYSTEM_PROMPT, format_context_with_citations
from src.agents.utils import format_context
from src.agents.citation_parser import CitationParser
from src.agents.citation_verifier import CitationVerifier
from src.retrieval.hybrid import hybrid_search
from src.retrieval.dense import dense_search
from src.ingestion.embedding import embed_single
from src.ingestion.chunker import count_tokens
from src.ingestion.bm25_builder import get_bm25_manager
from src.models.responses import DocumentSource, SourceChunk, SourceMetadata, GroupedDocumentResponse
from config.config import settings
from src.constants import MAX_CONTEXT_TOKENS, MIN_CONTEXT_LENGTH

DEFAULT_MAX_ITERATIONS = 3
DEFAULT_RETRIEVAL_K = 5

SPECIFIC_TERMS = ["điều khoản", "khoản", "điều", "nghị định", "thông tư", "luật"]


class AgenticRAG:
    """Agentic RAG with self-evaluation and iterative retrieval."""

    def __init__(
        self,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        retrieval_k: int = DEFAULT_RETRIEVAL_K,
    ):
        """Initialize Agentic RAG.

        Args:
            max_iterations: Maximum retrieval iterations
            retrieval_k: Top-k chunks to retrieve per iteration
        """
        self.max_iterations = max_iterations
        self.retrieval_k = retrieval_k
        # Initialize citation parser and verifier
        self.citation_parser = CitationParser()
        self.citation_verifier = CitationVerifier(
            grounding_threshold=getattr(settings, 'grounding_threshold', 0.7)
        )

    def select_strategy(self, query: str, bm25_available: bool = True) -> str:
        """Select retrieval strategy.

        Args:
            query: Query text
            bm25_available: Whether BM25 index is available

        Returns:
            Strategy: "dense" or "hybrid"
        """
        query_lower = query.lower()
        has_specific_terms = any(term in query_lower for term in SPECIFIC_TERMS)

        if has_specific_terms and bm25_available:
            return "hybrid"
        return "dense"

    async def _rewrite_query_with_history(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
    ) -> str:
        """Rewrite query using conversation history for better retrieval.

        Args:
            query: Current user query
            conversation_history: Optional conversation history

        Returns:
            Rewritten query for retrieval (or original if no history)
        """
        if not conversation_history:
            return query

        # Limit history by character count
        # Iterate from newest to oldest (reversed), skip messages that would exceed budget
        # This allows including older smaller messages even if newest is too large
        total_chars = 0
        limited_history = []
        for msg in reversed(conversation_history[-MAX_HISTORY_MESSAGES:]):
            msg_content = msg.get("content", "")
            if total_chars + len(msg_content) > MAX_CONTEXT_CHARS:
                continue
            total_chars += len(msg_content)
            limited_history.insert(0, msg)

        # Build context from limited history
        history_context = []
        for msg in limited_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role and content:
                history_context.append(f"{role}: {content}")

        if not history_context:
            return query

        # Use LLM to rewrite query for better retrieval
        system_prompt = (
            "Bạn là trợ lý chuyên về viết lại câu hỏi để tìm kiếm thông tin. "
            "Nhiệm vụ: Viết lại câu hỏi của người dùng thành câu hỏi đầy đủ và rõ ràng hơn, "
            "dựa vào lịch sử trò chuyện nếu cần thiết để giải quyết các đại từ như 'nó', 'cái đó'.\n\n"
            "QUAN TRỌNG: Chỉ trả lời CÂU HỎI đã viết lại, không giải thích gì thêm."
        )

        user_prompt = (
            f"Lịch sử trò chuyện:\n" + "\n".join(history_context) + "\n\n"
            f"Câu hỏi hiện tại: {query}\n\n"
            f"Viết lại câu hỏi để tìm kiếm thông tin tốt hơn:"
        )

        try:
            response = await chat_async(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # Low temperature for more deterministic rewriting
                max_tokens=256,
            )
            rewritten = response["content"].strip()
            # Return rewritten query if it's different and not too long
            if rewritten and rewritten != query and len(rewritten) < MAX_QUERY_REWRITE_LENGTH:
                return rewritten
        except Exception as e:
            logger.warning(f"Query rewrite failed: {e}, using original query")

        return query

    async def retrieve(
        self,
        query: str,
        query_embedding: list[float],
        user_id: UUID | str,
        bm25_index: Any,
        strategy: str,
    ) -> list[dict]:
        """Retrieve documents.

        Args:
            query: Query text
            query_embedding: Query embedding vector
            user_id: User ID for filtering
            bm25_index: Optional BM25 index
            strategy: Retrieval strategy

        Returns:
            Retrieved documents
        """
        if strategy == "hybrid" and bm25_index:
            return await hybrid_search(
                query_embedding=query_embedding,
                query_text=query,
                user_id=str(user_id),
                bm25_index=bm25_index,
                k=self.retrieval_k,
            )
        return dense_search(
            query_embedding=query_embedding,
            user_id=str(user_id),
            k=self.retrieval_k,
        )

    def _build_messages(
        self,
        query: str,
        docs: list[dict] | None,
        conversation_history: list[dict] | None = None,
        system_prompt: str | None = None,
    ) -> list[dict[str, str]]:
        """Build message list for LLM call.

        Args:
            query: User question
            docs: Retrieved documents (optional, for context)
            conversation_history: Optional conversation history
            system_prompt: System prompt (uses default if None)

        Returns:
            List of message dicts with role and content
        """
        # Use default system prompt if not provided
        if system_prompt is None:
            system_prompt = (
                "Bạn là trợ lý AI tư vấn pháp luật Việt Nam.\n\n"
                "Trước khi trả lời, hãy viết ra quá trình suy luận từng bước của bạn "
                "(phân tích câu hỏi, chọn lọc thông tin từ ngữ cảnh, đối chiếu luật) và đặt trong thẻ <thinking>...</thinking>. "
                "Sau đó đưa ra câu trả lời chính thức bên ngoài thẻ.\n\n"
                "Ví dụ:\n"
                "<thinking>\n"
                "- Phân tích câu hỏi của người dùng...\n"
                "- Đối chiếu với các tài liệu trong ngữ cảnh...\n"
                "- Rút ra kết luận...\n"
                "</thinking>\n"
                "[Câu trả lời chính thức ở đây]\n\n"
                "Yêu cầu:\n"
                "1. Trả lời DỰA TRÊN ngữ cảnh\n"
                "2. Trích dẫn nguồn (doc_id)\n"
                "3. Nếu thiếu thông tin, nói rõ\n"
                "4. Trả lời tiếng Việt\n"
                "5. Sử dụng lịch sử trò chuyện (nếu có) để hiểu ngữ cảnh của câu hỏi hiện tại"
            )

        # Build user content with context
        user_content = f"Câu hỏi: {query}\n"
        if docs:
            user_content += f"Ngữ cảnh:\n{format_context(docs)}\n\n"
        user_content += "Trả lời:"

        # Build messages list
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_content})

        return messages

    def evaluate_context(self, query: str, docs: list[dict]) -> bool:
        """Check if context is sufficient.

        Args:
            query: User query (currently unused, kept for interface consistency)
            docs: Retrieved documents

        Returns:
            True if sufficient, False otherwise
        """
        if not docs:
            return False

        context = format_context(docs)
        return len(context) >= MIN_CONTEXT_LENGTH

    async def generate_answer(
        self,
        query: str,
        docs: list[dict],
        conversation_history: list[dict] | None = None,
    ) -> str:
        """Generate answer from context (non-streaming).

        Args:
            query: User query
            docs: Retrieved documents
            conversation_history: Optional conversation history for context

        Returns:
            Generated answer
        """
        messages = self._build_messages(query, docs, conversation_history)

        response = await chat_async(
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )

        return response["content"]

    async def generate_answer_stream(
        self,
        query: str,
        docs: list[dict],
        conversation_history: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        """Generate streaming answer from context.

        Args:
            query: User query
            docs: Retrieved documents
            conversation_history: Optional conversation history for context

        Yields:
            Text chunks as they arrive from LLM
        """
        messages = self._build_messages(query, docs, conversation_history)

        async for chunk in chat_async_stream(
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        ):
            yield chunk

    def build_rag_context(
        self,
        chunks: list[dict],
        max_tokens: int = MAX_CONTEXT_TOKENS,
    ) -> tuple[str, int]:
        """Build RAG context with token budgeting.

        Args:
            chunks: List of retrieved chunks
            max_tokens: Maximum context tokens

        Returns:
            (formatted_context, total_tokens)
        """
        selected_chunks = []
        total_tokens = 0

        for chunk in chunks:
            chunk_text = chunk.get("text", chunk.get("content", ""))
            chunk_tokens = count_tokens(chunk_text)

            if total_tokens + chunk_tokens > max_tokens:
                break

            selected_chunks.append(chunk)
            total_tokens += chunk_tokens

        return format_context(selected_chunks), total_tokens

    async def query(
        self,
        query: str,
        user_id: UUID | str,
        initial_strategy: str | None = None,
        conversation_history: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Execute agentic RAG query (non-streaming).

        Args:
            query: User query
            user_id: User ID for filtering
            initial_strategy: Initial strategy or None for auto-select
            conversation_history: Optional conversation history for context

        Returns:
            Dict with answer, retrieval_history, status
        """
        retrieval_history = []
        all_docs = []
        strategy = initial_strategy or self.select_strategy(query, True)

        query_embedding = await asyncio.to_thread(embed_single, query)
        bm25_manager = get_bm25_manager()
        bm25_index = bm25_manager.get_index(user_id)

        # Rewrite query using conversation history for better retrieval
        retrieval_query = await self._rewrite_query_with_history(query, conversation_history)

        for iteration in range(self.max_iterations):
            docs = await self.retrieve(
                query=retrieval_query,  # Use rewritten query for retrieval
                query_embedding=query_embedding,
                user_id=user_id,
                bm25_index=bm25_index if bm25_index and bm25_index.doc_freqs else None,
                strategy=strategy,
            )

            new_docs = self._deduplicate_docs(all_docs, docs)
            all_docs.extend(new_docs)

            sufficient = self.evaluate_context(query, all_docs)

            retrieval_history.append({
                "iteration": iteration + 1,
                "strategy": strategy,
                "docs_retrieved": len(docs),
                "new_docs": len(new_docs),
                "sufficient": sufficient,
            })

            if sufficient:
                # GENERATION PASS 1: G-Cite with enhanced prompt
                answer = await self._generate_with_citation_aware_prompt(
                    query, all_docs, conversation_history
                )

                # VERIFICATION PASS
                parsed = self.citation_parser.parse(answer)
                verification = self.citation_verifier.verify(parsed, all_docs, answer)

                # CHECK IF REGENERATE NEEDED
                if self._should_regenerate(verification):
                    logger.debug("Citation verification failed, regenerating...")
                    answer = await self._regenerate_with_explicit_sources(
                        query, all_docs, verification, conversation_history
                    )
                    # 2nd verification for warnings
                    parsed = self.citation_parser.parse(answer)
                    verification = self.citation_verifier.verify(parsed, all_docs, answer)

                # Build response with verification metadata using grouped structure
                titles = await self._resolve_document_titles(all_docs)
                document_sources = self._group_by_document(all_docs, titles)

                # Create metadata
                top_document = document_sources[0].filename if document_sources else ""
                source_metadata = SourceMetadata(
                    total_documents=len(document_sources),
                    total_chunks=sum(ds.total_chunks_used for ds in document_sources),
                    top_document=top_document
                )

                # Build grouped response
                response = GroupedDocumentResponse(
                    content=answer,
                    sources=document_sources,
                    metadata=source_metadata
                )

                # Add legacy fields for backward compatibility
                response_dict = response.model_dump()
                response_dict["retrieval_history"] = retrieval_history
                response_dict["total_docs"] = len(all_docs)
                response_dict["iterations"] = iteration + 1
                response_dict["status"] = "success"
                response_dict["citation_verification"] = self.citation_verifier.get_summary_stats(verification)

                # Add legacy citations (flat list)
                response_dict["citations"] = response.get_legacy_citations()

                return response_dict

            strategy = self._switch_strategy(strategy, bm25_index)

        # Max iterations reached - same flow with available docs
        answer = await self._generate_with_citation_aware_prompt(
            query, all_docs, conversation_history
        )

        # Verification pass
        parsed = self.citation_parser.parse(answer)
        verification = self.citation_verifier.verify(parsed, all_docs, answer)

        # Check if regenerate needed
        if self._should_regenerate(verification):
            logger.debug("Citation verification failed on max iterations, regenerating...")
            answer = await self._regenerate_with_explicit_sources(
                query, all_docs, verification, conversation_history
            )
            parsed = self.citation_parser.parse(answer)
            verification = self.citation_verifier.verify(parsed, all_docs, answer)

        # Build grouped response with available docs
        titles = await self._resolve_document_titles(all_docs)
        document_sources = self._group_by_document(all_docs, titles)

        # Create metadata
        top_document = document_sources[0].filename if document_sources else ""
        source_metadata = SourceMetadata(
            total_documents=len(document_sources),
            total_chunks=sum(ds.total_chunks_used for ds in document_sources),
            top_document=top_document
        )

        # Build grouped response
        response = GroupedDocumentResponse(
            content=answer,
            sources=document_sources,
            metadata=source_metadata
        )

        # Add legacy fields for backward compatibility
        response_dict = response.model_dump()
        response_dict["retrieval_history"] = retrieval_history
        response_dict["total_docs"] = len(all_docs)
        response_dict["iterations"] = self.max_iterations
        response_dict["status"] = "max_iterations_reached"
        response_dict["citation_verification"] = self.citation_verifier.get_summary_stats(verification)

        # Add legacy citations (flat list)
        response_dict["citations"] = response.get_legacy_citations()

        return response_dict

    async def query_stream(
        self,
        query: str,
        user_id: UUID | str,
        initial_strategy: str | None = None,
        conversation_history: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """Execute agentic RAG query with streaming.

        Args:
            query: User query
            user_id: User ID for filtering
            initial_strategy: Initial strategy or None for auto-select
            conversation_history: Optional conversation history for context

        Yields:
            Dict chunks with type:
            - "retrieval": {iteration, strategy, docs_retrieved, new_docs, sufficient}
            - "content": {text}
            - "metadata": {total_docs, iterations, status, citations}
        """
        retrieval_history = []
        all_docs = []
        strategy = initial_strategy or self.select_strategy(query, True)

        query_embedding = await asyncio.to_thread(embed_single, query)
        bm25_manager = get_bm25_manager()
        bm25_index = bm25_manager.get_index(user_id)

        # Rewrite query using conversation history for better retrieval
        retrieval_query = await self._rewrite_query_with_history(query, conversation_history)

        for iteration in range(self.max_iterations):
            docs = await self.retrieve(
                query=retrieval_query,  # Use rewritten query for retrieval
                query_embedding=query_embedding,
                user_id=user_id,
                bm25_index=bm25_index if bm25_index and bm25_index.doc_freqs else None,
                strategy=strategy,
            )

            new_docs = self._deduplicate_docs(all_docs, docs)
            all_docs.extend(new_docs)

            sufficient = self.evaluate_context(query, all_docs)

            # Extract unique document information for enhanced display
            unique_doc_ids = set()
            doc_title_counts: dict[str, int] = {}

            for doc in docs:
                doc_id = doc.get("document_id")
                if doc_id:
                    unique_doc_ids.add(doc_id)
                    # Track chunk counts per document
                    doc_title_counts[doc_id] = doc_title_counts.get(doc_id, 0) + 1

            # Get top documents by chunk count (max 3 for display brevity)
            top_docs = sorted(
                doc_title_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]

            retrieval_history.append({
                "iteration": iteration + 1,
                "strategy": strategy,
                "chunks_retrieved": len(docs),  # Renamed from docs_retrieved for clarity
                "unique_documents": len(unique_doc_ids),  # Number of unique documents
                "top_documents": [doc_id for doc_id, _ in top_docs],  # Top doc IDs
                "new_docs": len(new_docs),
                "sufficient": sufficient,
            })

            # Emit retrieval status with document-level information
            yield {
                "type": "retrieval",
                "data": retrieval_history[-1],
            }

            if sufficient:
                # Stream content with citation-aware prompt
                content_chunk_count = 0
                full_response = ""

                logger.debug(f"[RAG STREAM] Starting content stream (iteration {iteration + 1})")

                # Use citation-aware prompt for streaming
                system_content = CITATION_AWARE_SYSTEM_PROMPT.format(
                    context_with_headers=format_context_with_citations(all_docs)
                )

                user_content = f"Câu hỏi: {query}\n\nTrả lời:"

                messages = [{"role": "system", "content": system_content}]
                if conversation_history:
                    messages.extend(conversation_history)
                messages.append({"role": "user", "content": user_content})

                # Apply post-processing to separate thinking from content
                raw_stream = chat_async_stream(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2048,
                )

                # Process stream to separate thinking and content
                thinking_yielded = False
                async for processed_chunk in stream_with_thinking_separation(raw_stream):
                    chunk_type = processed_chunk.get("type")
                    chunk_text = processed_chunk.get("text", "")

                    if not chunk_text:
                        continue

                    content_chunk_count += 1
                    full_response += chunk_text

                    if content_chunk_count <= 3 or content_chunk_count % 10 == 0:
                        logger.debug(f"[RAG STREAM] {chunk_type.upper()} chunk #{content_chunk_count}: {len(chunk_text)} chars")

                    # Yield thinking chunks (for UI display in thinking block)
                    if chunk_type == "thinking":
                        thinking_yielded = True
                        yield {
                            "type": "thinking",
                            "data": {"text": chunk_text},
                        }
                    # Yield content chunks (actual answer)
                    elif chunk_type == "content":
                        yield {
                            "type": "content",
                            "data": {"text": chunk_text},
                        }

                # DEBUG: Log if no thinking was yielded
                if not thinking_yielded:
                    logger.warning("[RAG STREAM] No thinking content was yielded - LLM may not be outputting <thinking> tags")

                logger.debug(f"[RAG STREAM] Completed content stream: {content_chunk_count} chunks")

                # Verification pass after streaming completes
                parsed = self.citation_parser.parse(full_response)
                verification = self.citation_verifier.verify(parsed, all_docs, full_response)

                # Check if regeneration is needed (streaming mode - emit warning instead)
                if self._should_regenerate(verification):
                    logger.warning("Citation verification failed in streaming mode, emitting warning")
                    yield {
                        "type": "warning",
                        "data": {
                            "message": "Một số citation không được verify. Vui lòng kiểm tra kỹ.",
                            "verification": self.citation_verifier.get_summary_stats(verification)
                        }
                    }

                # Resolve document titles and group by document
                titles = await self._resolve_document_titles(all_docs)
                document_sources = self._group_by_document(all_docs, titles)

                # Create metadata
                top_document = document_sources[0].filename if document_sources else ""

                # Convert DocumentSource objects to dicts for JSON serialization
                sources_data = [ds.model_dump() for ds in document_sources]

                # Extract legacy flat citations list for backward compatibility
                flat_citations = self._extract_citations(all_docs, titles)

                # Emit final metadata with grouped structure and verification stats
                yield {
                    "type": "metadata",
                    "data": {
                        "total_docs": len(all_docs),
                        "iterations": iteration + 1,
                        "status": "success",
                        "sources": sources_data,
                        "citations": flat_citations,
                        "citation_verification": self.citation_verifier.get_summary_stats(verification),
                        "metadata": {
                            "total_documents": len(document_sources),
                            "total_chunks": sum(ds.total_chunks_used for ds in document_sources),
                            "top_document": top_document
                        }
                    },
                }
                return

            strategy = self._switch_strategy(strategy, bm25_index)

        # Max iterations reached - stream with what we have (citation-aware)
        content_chunk_count = 0
        full_response = ""

        logger.debug(f"[RAG STREAM] Max iterations reached, starting content stream")

        # Use citation-aware prompt
        system_content = CITATION_AWARE_SYSTEM_PROMPT.format(
            context_with_headers=format_context_with_citations(all_docs)
        )

        user_content = f"Câu hỏi: {query}\n\nTrả lời:"

        messages = [{"role": "system", "content": system_content}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_content})

        async for chunk in chat_async_stream(
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        ):
            content_chunk_count += 1
            full_response += chunk
            if content_chunk_count <= 3 or content_chunk_count % 10 == 0:
                logger.debug(f"[RAG STREAM] Content chunk #{content_chunk_count}: {len(chunk)} chars")
            yield {
                "type": "content",
                "data": {"text": chunk},
            }
        logger.debug(f"[RAG STREAM] Completed content stream: {content_chunk_count} chunks")

        # Verification pass
        parsed = self.citation_parser.parse(full_response)
        verification = self.citation_verifier.verify(parsed, all_docs, full_response)

        # Emit warning if verification failed
        if self._should_regenerate(verification):
            yield {
                "type": "warning",
                "data": {
                    "message": "Một số citation không được verify. Vui lòng kiểm tra kỹ.",
                    "verification": self.citation_verifier.get_summary_stats(verification)
                }
            }

        # Resolve document titles and group by document
        titles = await self._resolve_document_titles(all_docs)
        document_sources = self._group_by_document(all_docs, titles)

        # Create metadata
        top_document = document_sources[0].filename if document_sources else ""

        # Convert DocumentSource objects to dicts for JSON serialization
        sources_data = [ds.model_dump() for ds in document_sources]

        # Extract legacy flat citations list for backward compatibility
        flat_citations = self._extract_citations(all_docs, titles)

        yield {
            "type": "metadata",
            "data": {
                "total_docs": len(all_docs),
                "iterations": self.max_iterations,
                "status": "max_iterations_reached",
                "sources": sources_data,
                "citations": flat_citations,
                "citation_verification": self.citation_verifier.get_summary_stats(verification),
                "metadata": {
                    "total_documents": len(document_sources),
                    "total_chunks": sum(ds.total_chunks_used for ds in document_sources),
                    "top_document": top_document
                }
            },
        }

    async def _resolve_document_titles(self, docs: list[dict]) -> dict[str, str]:
        """Fetch document filenames for document_ids from Postgres using batch query."""
        doc_ids = {d.get("document_id") for d in docs if d.get("document_id")}
        if not doc_ids:
            return {}

        from src.database.session import async_session_factory
        from src.indexing.document_store import get_documents_batch

        async with async_session_factory() as session:
            # Single batch query instead of N+1 individual queries
            titles = await get_documents_batch(
                document_ids=list(doc_ids),
                db=session,
            )
        return titles

    def _extract_citations(self, docs: list[dict], doc_titles: dict[str, str] | None = None, max_citations: int | None = None) -> list[dict]:
        """Extract citation info from retrieved docs.

        Args:
            docs: Retrieved documents
            doc_titles: Pre-resolved document titles
            max_citations: Maximum citations to extract (defaults to settings.max_citations)

        Returns:
            List of citation dicts
        """
        from config.config import settings

        if max_citations is None:
            max_citations = settings.max_citations
        if max_citations <= 0:
            max_citations = DEFAULT_MAX_CITATIONS

        snippet_length = settings.snippet_length
        citations = []
        doc_titles = doc_titles or {}
        for index, doc in enumerate(docs[:max_citations]):
            doc_id = doc.get("document_id")
            title = doc_titles.get(str(doc_id)) or doc.get("metadata", {}).get("title") or doc.get("title") or "Tài liệu không rõ"
            chunk_id = doc.get("chunk_id") or doc.get("id") or f"chunk-{index}"

            # Extract content and generate snippet
            content = doc.get("text") or doc.get("content") or ""
            content = content if isinstance(content, str) else str(content)
            content_length = len(content)
            snippet = content[:snippet_length]
            if content_length > snippet_length:
                snippet += "..."

            citations.append({
                "chunk_id": str(chunk_id),
                "source": title,
                "title": title,
                "snippet": snippet,
                "content": content,
                "content_length": content_length,
                "page_number": doc.get("page_number") or doc.get("metadata", {}).get("page_number"),
                "score": float(doc.get("score") or doc.get("rrf_score") or 0.0),
                "document_id": str(doc_id) if doc_id else None,
                "chunk_index": doc.get("chunk_index"),
            })
        return citations

    def _group_by_document(
        self,
        docs: list[dict],
        doc_titles: dict[str, str] | None = None,
        max_chunks_per_doc: int | None = None
    ) -> list[DocumentSource]:
        """Group retrieved chunks by their source documents.

        This creates a user-friendly structure where chunks are organized
        by their originating documents, making it clear which documents
        contributed to the answer and how many chunks from each.

        Args:
            docs: Retrieved document chunks
            doc_titles: Pre-resolved document titles (document_id → filename/title)
            max_chunks_per_doc: Maximum chunks to include per document

        Returns:
            List of DocumentSource objects, each representing one document
            with its associated chunks
        """
        from config.config import settings

        if max_chunks_per_doc is None:
            max_chunks_per_doc = settings.max_citations or DEFAULT_MAX_CITATIONS

        doc_titles = doc_titles or {}
        snippet_length = settings.snippet_length

        # Group chunks by document_id
        docs_by_document: dict[str, list[dict]] = {}
        for doc in docs:
            doc_id = doc.get("document_id") or doc.get("metadata", {}).get("document_id", "unknown")
            if doc_id not in docs_by_document:
                docs_by_document[doc_id] = []
            docs_by_document[doc_id].append(doc)

        # Create DocumentSource for each document
        document_sources = []

        for doc_id, chunks in docs_by_document.items():
            # Sort chunks by score (descending)
            sorted_chunks = sorted(
                chunks,
                key=lambda d: float(d.get("score") or d.get("rrf_score") or 0.0),
                reverse=True
            )[:max_chunks_per_doc]

            if not sorted_chunks:
                continue

            # Get document metadata
            title = (
                doc_titles.get(str(doc_id)) or
                sorted_chunks[0].get("metadata", {}).get("title") or
                sorted_chunks[0].get("title") or
                "Tài liệu không rõ"
            )

            # Calculate aggregate relevance score for this document
            scores = [
                float(d.get("score") or d.get("rrf_score") or 0.0)
                for d in sorted_chunks
            ]
            avg_relevance = sum(scores) / len(scores) if scores else 0.0

            # Create SourceChunk objects
            source_chunks = []
            for chunk in sorted_chunks:
                content = chunk.get("text") or chunk.get("content") or ""
                content = content if isinstance(content, str) else str(content)
                snippet = content[:snippet_length]
                if len(content) > snippet_length:
                    snippet += "..."

                source_chunks.append(SourceChunk(
                    chunk_id=chunk.get("chunk_id") or chunk.get("id") or f"chunk-{hash(content)}",
                    page=chunk.get("page_number") or chunk.get("metadata", {}).get("page_number"),
                    snippet=snippet,
                    score=float(chunk.get("score") or chunk.get("rrf_score") or 0.0),
                    content=content
                ))

            # Create DocumentSource
            document_source = DocumentSource(
                document_id=doc_id if isinstance(doc_id, str) else str(doc_id),
                filename=title,  # Using title as filename for now
                title=title,
                total_chunks_used=len(source_chunks),
                relevance_score=avg_relevance,
                chunks=source_chunks
            )

            document_sources.append(document_source)

        # Sort documents by relevance score (descending)
        document_sources.sort(key=lambda ds: ds.relevance_score, reverse=True)

        return document_sources

    def _deduplicate_docs(self, existing: list[dict], new: list[dict]) -> list[dict]:
        """Remove duplicate docs by chunk_id or id."""
        seen_ids = {
            d.get("chunk_id") or d.get("id") 
            for d in existing 
            if d.get("chunk_id") or d.get("id")
        }
        return [
            d for d in new 
            if (d.get("chunk_id") or d.get("id")) not in seen_ids
        ]

    def _switch_strategy(self, current: str, bm25_index: Any) -> str:
        """Switch strategy for next iteration."""
        if current == "hybrid":
            return "dense"
        if current == "dense" and bm25_index and bm25_index.doc_freqs:
            return "hybrid"
        return "dense"

    def _build_success_response(
        self,
        answer: str,
        history: list,
        docs: list,
        iterations: int,
    ) -> dict:
        """Build success response."""
        return {
            "content": answer,
            "retrieval_history": history,
            "total_docs": len(docs),
            "iterations": iterations,
            "status": "success",
        }

    def _build_max_iterations_response(
        self,
        answer: str,
        history: list,
        docs: list,
    ) -> dict:
        """Build max iterations reached response."""
        return {
            "content": answer,
            "retrieval_history": history,
            "total_docs": len(docs),
            "iterations": self.max_iterations,
            "status": "max_iterations_reached",
        }

    async def _generate_with_citation_aware_prompt(
        self,
        query: str,
        docs: list[dict],
        conversation_history: list[dict] | None = None
    ) -> str:
        """Generate answer with citation-aware prompt.

        Args:
            query: User question
            docs: Retrieved documents
            conversation_history: Optional conversation history

        Returns:
            Generated answer with inline citation markers
        """
        system_content = CITATION_AWARE_SYSTEM_PROMPT.format(
            context_with_headers=format_context_with_citations(docs)
        )

        user_content = f"Câu hỏi: {query}\n\nTrả lời:"

        messages = [{"role": "system", "content": system_content}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_content})

        response = await chat_async(
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )

        return response["content"]

    def _should_regenerate(self, verification: dict) -> bool:
        """Decide whether to regenerate based on verification results.

        Args:
            verification: Results from CitationVerifier.verify()

        Returns:
            True if regeneration is needed
        """
        # Regenerate if any hallucinated citations
        if verification.get("hallucinated"):
            return True

        # Regenerate if too many uncited claims (>3)
        if len(verification.get("missing", [])) > 3:
            return True

        return False

    async def _regenerate_with_explicit_sources(
        self,
        query: str,
        docs: list[dict],
        failed_verification: dict,
        conversation_history: list[dict] | None = None
    ) -> str:
        """Regenerate with explicit source mapping.

        Args:
            query: User question
            docs: Retrieved documents
            failed_verification: Previous verification results
            conversation_history: Optional conversation history

        Returns:
            Regenerated answer
        """
        # Build explicit source list
        source_list = "\n".join([
            f"- [{doc.get('chunk_id', doc.get('id', ''))[:8]}] {doc.get('metadata', {}).get('title', 'Unknown')}"
            for doc in docs[:5]
        ])

        system_content = f"""
TRƯỜNG HỢP CÁC BẠN:
1. PHẢI trích dẫn source cho mỗi claim
2. Chỉ sử dụng sources trong list này:
{source_list}
3. Format: [source:chunk_id]
4. KHÔNG tạo ra citations mới
"""

        user_content = f"Câu hỏi: {query}\n\nTrả lời:"
        messages = [{"role": "system", "content": system_content}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_content})

        response = await chat_async(
            messages=messages,
            temperature=0.3,  # Lower temperature for more deterministic output
            max_tokens=2048,
        )

        return response["content"]


async def generate_response(
    query: str,
    user_id: UUID | str,
    conversation_history: list[dict] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    stream_callback: Any = None,
) -> dict:
    """Legacy: Generate RAG response.

    Args:
        query: User query
        user_id: User ID for filtering
        conversation_history: Optional conversation history
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        stream_callback: Optional streaming callback

    Returns:
        Response dict with content, citations, metadata
    """
    agent = AgenticRAG(max_iterations=1)
    result = await agent.query(query, user_id)

    return {
        "content": result["content"],
        "citations": [],
        "sources": [],
        "metadata": {
            "agent": "rag",
            "chunks_found": result["total_docs"],
        },
    }


async def generate_response_simple(
    query: str,
    context_chunks: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> dict:
    """Legacy: Generate RAG response from pre-retrieved chunks.

    Args:
        query: User query
        context_chunks: Pre-retrieved context chunks
        temperature: Sampling temperature
        max_tokens: Max tokens to generate

    Returns:
        Response dict with content and citations
    """
    if not context_chunks:
        return {
            "content": f"Không tìm thấy thông tin liên quan đến \"{query}\".",
            "citations": [],
            "metadata": {"agent": "rag", "chunks_found": 0},
        }

    prompt = ANSWER_GENERATOR_PROMPT.format(
        query=query,
        context=format_context(context_chunks),
    )

    response = await chat_async(
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return {
        "content": response["content"],
        "citations": [],
        "metadata": {
            "agent": "rag",
            "chunks_found": len(context_chunks),
        },
    }


__all__ = [
    "AgenticRAG",
    "generate_response",
    "generate_response_simple",
]
