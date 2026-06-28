"""
RetrievalAgent: Merged query refinement + retrieval + reranking (4-agent architecture)

This agent consolidates three former agents into one unified retrieval workflow:
- QueryRefinerAgent: Query expansion and refinement
- RetrievalAgent: Multi-stage document retrieval
- RerankingAgent: Cross-encoder reranking for precision

Architecture:
    Input: RAGState (query, user_id)
    Step 1: Query refinement (LLM + synonym expansion)
    Step 2: Hybrid retrieval (Dense + BM25 with RRF)
    Step 3: Reranking (Cross-encoder or content overlap)
    Output: RAGState with retrieval_agent_output

Example:
    agent = RetrievalAgent(config=RetrievalAgentConfig(), llm_client=llm)
    state = await agent.handle(state)
    docs = get_retrieval_docs(state)
"""

import json
import logging
import re
from typing import List, Dict, Any, AsyncIterator, Optional
import time
from uuid import UUID

from src.shared.ports.llm import LLMPort
from src.shared.ports.embedding import EmbeddingPort
from src.config.config import settings
from src.modules.retrieval.application.search_use_case import SearchUseCase
from src.modules.rag.orchestration.state.rag_state import (
    RAGState,
    AgentStatus,
    DocumentWithScore,
    RetrievalMetadata,
    RetrievalStrategy,
    RetrievalAgentConfig,
    create_agent_result,
    mark_agent_start,
    update_state_with_agent_result,
    update_retrieval_output,
)

logger = logging.getLogger(__name__)


class RetrievalAgent:
    """
    Unified retrieval agent merging query refinement, retrieval, and reranking.

    Merged functionality from:
    - QueryRefinerAgent: Query expansion using LLM and synonyms
    - RetrievalAgent: Hybrid retrieval (Dense + BM25)
    - RerankingAgent: Cross-encoder reranking

    This consolidation reduces coordination overhead and improves performance.

    Attributes:
        config: RetrievalAgentConfig with merged settings
        llm_client: LLM client for query refinement
    """

    def __init__(
        self,
        config: RetrievalAgentConfig,
        llm_client: Optional[LLMPort] = None,
        embedding: EmbeddingPort | None = None,
        search: SearchUseCase | None = None,
    ):
        """
        Initialize RetrievalAgent.

        Args:
            config: Merged configuration from QueryRefinerAgent + RetrievalAgent + RerankingAgent
            llm_client: Optional LLM client for query refinement
            embedding: Embedding port for query vectorization
            search: Retrieval application service
        """
        self.config = config
        self.llm_client = llm_client
        self.embedding = embedding
        self.search = search
        self._reranker = None  # Lazy-loaded reranker

    async def handle(self, state: RAGState, context: Optional[Dict[str, Any]] = None) -> RAGState:
        """
        Execute full retrieval workflow: refine -> retrieve -> rerank.

        This is the main entry point for the retrieval agent. It executes
        all three stages sequentially and updates the state with combined results.

        Args:
            state: Current RAGState with query and user_id
            context: Optional additional context

        Returns:
            Updated RAGState with retrieval_agent_output populated
        """
        start_time = time.time()
        state = mark_agent_start(state, "RetrievalAgent")

        try:
            query = state["query"]
            user_id = state["user_id"]

            logger.info(f"RetrievalAgent starting: query='{query[:50]}...', user={user_id}")

            # Stage 1: Query refinement (merged from QueryRefinerAgent)
            refined_queries = await self._refine_query(query, state)
            logger.info(f"Query refinement: generated {len(refined_queries)} queries")

            # Stage 2: Document retrieval (original RetrievalAgent)
            retrieved_docs, retrieval_metadata = await self._retrieve_documents(
                queries=refined_queries, user_id=user_id
            )
            logger.info(f"Retrieval: found {len(retrieved_docs)} documents")

            # Stage 3: Reranking (merged from RerankingAgent)
            reranked_docs = await self._rerank_documents(query=query, documents=retrieved_docs)
            logger.info(f"Reranking: {len(reranked_docs)} documents after reranking")

            # Update state with combined output
            state = update_retrieval_output(
                state=state,
                refined_queries=refined_queries,
                retrieved_docs=retrieved_docs,
                reranked_docs=reranked_docs,
                metadata=retrieval_metadata,
            )

            execution_time = (time.time() - start_time) * 1000
            result = create_agent_result(
                agent_name="RetrievalAgent",
                status=AgentStatus.COMPLETED,
                execution_time_ms=execution_time,
                metadata={
                    "refined_queries": len(refined_queries),
                    "retrieved_docs": len(retrieved_docs),
                    "reranked_docs": len(reranked_docs),
                    "strategy": str(retrieval_metadata.strategy)
                    if retrieval_metadata
                    else "unknown",
                },
            )

            logger.info(f"RetrievalAgent completed in {execution_time:.0f}ms")
            return update_state_with_agent_result(state, result)

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"RetrievalAgent failed: {e}", exc_info=True)

            result = create_agent_result(
                agent_name="RetrievalAgent",
                status=AgentStatus.FAILED,
                execution_time_ms=execution_time,
                error_message=str(e),
            )

            # Set empty results on failure
            state = update_retrieval_output(
                state=state, refined_queries=[state["query"]], retrieved_docs=[], reranked_docs=[]
            )
            return update_state_with_agent_result(state, result)

    async def handle_stream(
        self, state: RAGState, context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute retrieval with streaming progress updates.

        Yields progress updates for each stage:
        - Stage 1: Query refinement progress
        - Stage 2: Retrieval progress
        - Stage 3: Reranking progress

        Args:
            state: Current RAGState
            context: Optional additional context

        Yields:
            Streaming chunks with progress updates
        """
        start_time = time.time()
        state = mark_agent_start(state, "RetrievalAgent")

        try:
            query = state["query"]
            user_id = state["user_id"]

            yield {"type": "stage", "data": {"stage": "query_refinement", "status": "started"}}

            # Stage 1: Query refinement
            refined_queries = await self._refine_query(query, state)

            yield {
                "type": "stage",
                "data": {
                    "stage": "query_refinement",
                    "status": "completed",
                    "refined_queries": len(refined_queries),
                },
            }

            # Stage 2: Retrieval
            yield {"type": "stage", "data": {"stage": "retrieval", "status": "started"}}

            retrieved_docs, retrieval_metadata = await self._retrieve_documents(
                queries=refined_queries, user_id=user_id
            )

            yield {
                "type": "stage",
                "data": {
                    "stage": "retrieval",
                    "status": "completed",
                    "retrieved_docs": len(retrieved_docs),
                },
            }

            # Stage 3: Reranking
            yield {"type": "stage", "data": {"stage": "reranking", "status": "started"}}

            reranked_docs = await self._rerank_documents(query, retrieved_docs)

            # Update state
            state = update_retrieval_output(
                state=state,
                refined_queries=refined_queries,
                retrieved_docs=retrieved_docs,
                reranked_docs=reranked_docs,
                metadata=retrieval_metadata,
            )

            execution_time = (time.time() - start_time) * 1000
            result = create_agent_result(
                agent_name="RetrievalAgent",
                status=AgentStatus.COMPLETED,
                execution_time_ms=execution_time,
            )
            state = update_state_with_agent_result(state, result)

            yield {
                "type": "stage",
                "data": {
                    "stage": "reranking",
                    "status": "completed",
                    "reranked_docs": len(reranked_docs),
                },
            }

            yield {"type": "done", "data": {"total_time_ms": execution_time}}

        except Exception as e:
            logger.error(f"RetrievalAgent streaming failed: {e}")
            yield {"type": "error", "data": {"message": str(e)}}

    def can_handle(self, state: RAGState) -> bool:
        """
        Check if retrieval agent can handle the current state.

        RetrievalAgent handles all states with valid queries.

        Args:
            state: Current RAGState

        Returns:
            True if state has required fields
        """
        return bool(state.get("query") and state.get("user_id"))

    # ==========================================================================
    # Stage 1: Query Refinement (merged from QueryRefinerAgent)
    # ==========================================================================

    async def _refine_query(self, query: str, state: RAGState) -> List[str]:
        """
        Refine and expand query using LLM and synonyms.

        Merged functionality from QueryRefinerAgent.

        Args:
            query: Original query
            state: Current RAGState

        Returns:
            List of refined queries (includes original if preserve_original=True)
        """
        refined_queries: List[str] = []

        # Always include original if configured
        if self.config.preserve_original:
            refined_queries.append(query)

        # LLM-based expansion
        if self.config.use_llm_expansion and self.llm_client:
            # TODO: Implement LLM-based query expansion
            # This would call llm_client.generate() with expansion prompt
            # For now, add placeholder
            pass

        # Synonym-based expansion
        if self.config.use_synonym_expansion:
            synonym_expansions = self._synonym_expansion(query)
            refined_queries.extend(synonym_expansions)

        # Deduplicate
        unique_queries: List[str] = []
        seen = set()
        for q in refined_queries:
            normalized = q.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique_queries.append(q)

        return unique_queries[: self.config.expansion_count]

    def _synonym_expansion(self, query: str) -> List[str]:
        """
        Generate synonym-based query expansions.

        TODO: Enhance with WordNet or domain-specific synonym dictionaries.

        Args:
            query: Original query

        Returns:
            List of synonym-expanded queries
        """
        synonym_map = settings.query_expansion_synonyms

        expansions = []
        for word, synonyms in synonym_map.items():
            if word.lower() in query.lower():
                for synonym in synonyms[:2]:  # Limit expansions
                    expanded = query.lower().replace(word, synonym, 1)
                    if expanded != query:
                        expansions.append(expanded)

        return expansions[:2]

    # ==========================================================================
    # Stage 2: Document Retrieval (original RetrievalAgent)
    # ==========================================================================

    async def _retrieve_documents(
        self, queries: List[str], user_id: str
    ) -> tuple[List[DocumentWithScore], RetrievalMetadata]:
        """
        Execute hybrid document retrieval.

        Integrates with src.modules.retrieval for actual hybrid search.

        Args:
            queries: List of refined queries
            user_id: User ID for personalized search

        Returns:
            Tuple of (retrieved_docs, metadata)
        """
        start_time = time.time()

        # Use primary query for retrieval
        primary_query = queries[0] if queries else ""

        if not primary_query:
            logger.warning("No query provided for retrieval")
            return [], RetrievalMetadata(
                strategy=RetrievalStrategy.HYBRID,
                total_results=0,
                query_expansions=[],
                search_time_ms=0,
            )

        try:
            if self.embedding is None or self.search is None:
                raise RuntimeError(
                    "RetrievalAgent requires EmbeddingPort and SearchUseCase dependencies. "
                    "Compose them in the outer application/infrastructure layer."
                )

            # Generate embedding for query
            query_embedding = await self.embedding.embed(primary_query)

            # Execute hybrid search
            search_results = await self.search.execute(
                query_embedding=query_embedding,
                query_text=primary_query,
                user_id=user_id,
                k=self.config.top_k,
                rrf_k=60,
                enable_rerank=False,
            )

            # Convert to DocumentWithScore objects
            retrieved_docs = []
            for result in search_results:
                doc_id = self._extract_document_id(result)
                if doc_id is None:
                    logger.warning(
                        "Skipping search result without a valid document UUID: "
                        f"keys={list(result.keys())}, metadata_keys={list(result.get('metadata', {}).keys())}"
                    )
                    continue

                doc = DocumentWithScore(
                    doc_id=doc_id,
                    content=result.get("text", result.get("content", "")),
                    filename=result.get(
                        "filename", result.get("metadata", {}).get("title", "Unknown")
                    ),
                    page_number=result.get(
                        "page_number", result.get("metadata", {}).get("page", 0)
                    ),
                    chunk_index=result.get(
                        "chunk_index", result.get("metadata", {}).get("chunk_index", 0)
                    ),
                    score=result.get("rrf_score", result.get("score", 0.0)),
                    metadata=result.get("metadata", {}),
                )
                retrieved_docs.append(doc)

            search_time = (time.time() - start_time) * 1000

            metadata = RetrievalMetadata(
                strategy=RetrievalStrategy.HYBRID,
                total_results=len(retrieved_docs),
                query_expansions=queries[1:] if len(queries) > 1 else [],
                search_time_ms=search_time,
            )

            logger.info(f"Retrieved {len(retrieved_docs)} documents in {search_time:.0f}ms")
            return retrieved_docs, metadata

        except Exception as e:
            logger.error(f"Document retrieval failed: {e}", exc_info=True)
            search_time = (time.time() - start_time) * 1000

            return [], RetrievalMetadata(
                strategy=RetrievalStrategy.HYBRID,
                total_results=0,
                query_expansions=[],
                search_time_ms=search_time,
            )

    def _extract_document_id(self, result: Dict[str, Any]) -> UUID | None:
        """Extract a stable UUID from a search result or its metadata."""
        metadata = result.get("metadata") or {}
        candidates = (
            result.get("document_id"),
            metadata.get("document_id"),
            result.get("doc_id"),
            metadata.get("doc_id"),
            result.get("chunk_id"),
            result.get("id"),
        )

        for candidate in candidates:
            if not candidate:
                continue

            try:
                return candidate if isinstance(candidate, UUID) else UUID(str(candidate))
            except (TypeError, ValueError):
                continue

        return None

    # ==========================================================================
    # Stage 3: Reranking (merged from RerankingAgent)
    # ==========================================================================

    async def _rerank_documents(
        self, query: str, documents: List[DocumentWithScore]
    ) -> List[DocumentWithScore]:
        """
        Rerank documents using structured LLM output or content overlap fallback.

        Merged functionality from RerankingAgent.

        Args:
            query: Original query
            documents: List of retrieved documents

        Returns:
            Reranked documents (top-k after filtering)
        """
        if not documents or not self.config.enable_reranking:
            return documents

        if self.llm_client is None:
            logger.warning("LLM reranking skipped because llm_client is not configured")
            return self._fallback_reranking(query, documents)

        try:
            return await self._llm_reranking(query, documents)
        except Exception as e:
            logger.warning("LLM reranking failed, using content-overlap fallback: %s", e)
            return self._fallback_reranking(query, documents)

    async def _llm_reranking(
        self, query: str, documents: List[DocumentWithScore]
    ) -> List[DocumentWithScore]:
        """Rerank documents through deterministic structured JSON from the LLM."""
        prompt = self._build_llm_reranking_prompt(query, documents)
        raw = await self.llm_client.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1200,
        )
        rankings = self._parse_llm_reranking_response(raw, len(documents))
        reranked_docs = self._apply_llm_rankings(documents, rankings)

        if not reranked_docs:
            raise ValueError("LLM reranking returned no valid rankings")

        logger.info(
            "LLM reranking completed: candidates=%s, returned=%s",
            len(documents),
            min(len(reranked_docs), self.config.rerank_top_k),
        )
        return reranked_docs[: self.config.rerank_top_k]

    def _build_llm_reranking_prompt(self, query: str, documents: List[DocumentWithScore]) -> str:
        """Build a structured-output reranking prompt."""
        formatted_docs = []
        for index, doc in enumerate(documents):
            content = doc.content[:1200]
            formatted_docs.append(
                "\n".join(
                    [
                        f"[{index}] filename={doc.filename}",
                        f"page={doc.page_number}, chunk={doc.chunk_index}, retrieval_score={doc.score:.4f}",
                        f"content={content}",
                    ]
                )
            )

        return f"""Bạn là bộ reranker cho hệ thống RAG tiếng Việt.

Nhiệm vụ: xếp hạng các đoạn tài liệu theo mức độ hữu ích để trả lời câu hỏi.

CÂU HỎI:
{query}

TÀI LIỆU ỨNG VIÊN:
{chr(10).join(formatted_docs)}

Trả về DUY NHẤT một JSON object hợp lệ theo schema:
{{
  "rankings": [
    {{"index": ..., "score": ..., "reason": "lý do rất ngắn"}}
  ]
}}

Quy tắc:
- "index" phải là chỉ số tài liệu trong danh sách ứng viên.
- "score" là độ liên quan từ 0.0 đến 1.0.
- Sắp xếp "rankings" từ liên quan nhất đến ít liên quan nhất.
- Chỉ đưa vào "rankings" các đoạn có thông tin trực tiếp hoặc hỗ trợ rõ ràng cho câu hỏi.
- Bỏ qua đoạn không giúp trả lời câu hỏi; không cần trả đủ số lượng nếu chỉ có ít đoạn liên quan.
- Ưu tiên đoạn trực tiếp chứa quy định, điều khoản, điều kiện, quy trình, mốc thời gian, đối tượng áp dụng.
- Không loại bỏ tài liệu chỉ vì retrieval_score thấp nếu nội dung trả lời trực tiếp câu hỏi.
- Không thêm markdown, không giải thích ngoài JSON."""

    def _parse_llm_reranking_response(self, raw: str, num_documents: int) -> List[Dict[str, Any]]:
        """Parse and validate structured LLM reranking output."""
        text = (raw or "").strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                raise
            parsed = json.loads(match.group(0))

        if not isinstance(parsed, dict):
            raise ValueError("Expected JSON object from LLM reranking")

        raw_rankings = parsed.get("rankings")
        if not isinstance(raw_rankings, list):
            raise ValueError("LLM reranking response missing rankings list")

        rankings: List[Dict[str, Any]] = []
        seen: set[int] = set()
        for item in raw_rankings:
            if not isinstance(item, dict):
                continue
            try:
                index = int(item.get("index"))
                score = float(item.get("score", 0.0))
            except (TypeError, ValueError):
                continue
            if index < 0 or index >= num_documents or index in seen:
                continue
            seen.add(index)
            rankings.append(
                {
                    "index": index,
                    "score": max(0.0, min(1.0, score)),
                    "reason": str(item.get("reason") or ""),
                }
            )

        return rankings

    def _apply_llm_rankings(
        self,
        documents: List[DocumentWithScore],
        rankings: List[Dict[str, Any]],
    ) -> List[DocumentWithScore]:
        """Convert validated LLM rankings back into DocumentWithScore objects."""
        reranked_docs: List[DocumentWithScore] = []
        seen: set[int] = set()

        for ranking in rankings:
            index = int(ranking["index"])
            score = float(ranking["score"])
            if score < self.config.rerank_threshold:
                continue

            original = documents[index]
            reranked_docs.append(
                DocumentWithScore(
                    doc_id=original.doc_id,
                    content=original.content,
                    filename=original.filename,
                    page_number=original.page_number,
                    chunk_index=original.chunk_index,
                    score=score,
                    metadata={
                        **original.metadata,
                        "original_score": original.score,
                        "rerank_reason": ranking.get("reason", ""),
                        "reranker": "llm_structured",
                    },
                )
            )
            seen.add(index)

        if reranked_docs:
            return reranked_docs

        logger.info(
            "LLM reranking returned no documents above threshold; "
            "falling back to the highest-ranked candidate. threshold=%s",
            self.config.rerank_threshold,
        )

        if rankings:
            top_index = int(rankings[0]["index"])
            doc = documents[top_index]
            return [
                DocumentWithScore(
                    doc_id=doc.doc_id,
                    content=doc.content,
                    filename=doc.filename,
                    page_number=doc.page_number,
                    chunk_index=doc.chunk_index,
                    score=float(rankings[0]["score"]),
                    metadata={
                        **doc.metadata,
                        "original_score": doc.score,
                        "rerank_reason": rankings[0].get("reason", ""),
                        "reranker": "llm_structured_threshold_fallback",
                    },
                )
            ]

        for index, doc in enumerate(documents):
            if index in seen or len(reranked_docs) >= self.config.rerank_top_k:
                continue
            reranked_docs.append(
                DocumentWithScore(
                    doc_id=doc.doc_id,
                    content=doc.content,
                    filename=doc.filename,
                    page_number=doc.page_number,
                    chunk_index=doc.chunk_index,
                    score=doc.score,
                    metadata={
                        **doc.metadata,
                        "original_score": doc.score,
                        "reranker": "retrieval_order_fill",
                    },
                )
            )

        return reranked_docs

    def _fallback_reranking(
        self, query: str, documents: List[DocumentWithScore]
    ) -> List[DocumentWithScore]:
        """
        Fallback reranking using content overlap.

        TODO: Enhance with more sophisticated scoring.

        Args:
            query: Search query
            documents: List of documents

        Returns:
            Reranked documents
        """
        query_terms = set(query.lower().split())
        reranked_docs = []

        for doc in documents:
            content_terms = set(doc.content.lower().split()[:100])  # First 100 words
            overlap = len(query_terms & content_terms)
            boost = overlap / max(len(query_terms), 1)

            # Create new document with boosted score
            reranked_doc = DocumentWithScore(
                doc_id=doc.doc_id,
                content=doc.content,
                filename=doc.filename,
                page_number=doc.page_number,
                chunk_index=doc.chunk_index,
                score=min(1.0, doc.score + (boost * 0.2)),
                metadata=doc.metadata,
            )
            reranked_docs.append(reranked_doc)

        # Sort and filter
        reranked_docs.sort(key=lambda x: x.score, reverse=True)
        filtered = [d for d in reranked_docs if d.score >= self.config.rerank_threshold]

        if filtered:
            return filtered[: self.config.rerank_top_k]

        logger.warning(
            "Fallback reranking threshold filtered all documents; "
            f"returning top {self.config.rerank_top_k} by boosted score instead. "
            f"threshold={self.config.rerank_threshold}, "
            f"max_score={reranked_docs[0].score if reranked_docs else 0.0:.4f}"
        )
        return reranked_docs[: self.config.rerank_top_k]
