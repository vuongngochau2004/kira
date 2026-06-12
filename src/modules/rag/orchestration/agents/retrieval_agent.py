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

import logging
from typing import List, Dict, Any, AsyncIterator, Optional
import time

from src.shared.ports.llm import LLMPort
from src.shared.ports.embedding import EmbeddingPort
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
    update_retrieval_output
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

    async def handle(
        self,
        state: RAGState,
        context: Optional[Dict[str, Any]] = None
    ) -> RAGState:
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
                queries=refined_queries,
                user_id=user_id
            )
            logger.info(f"Retrieval: found {len(retrieved_docs)} documents")

            # Stage 3: Reranking (merged from RerankingAgent)
            reranked_docs = await self._rerank_documents(
                query=query,
                documents=retrieved_docs
            )
            logger.info(f"Reranking: {len(reranked_docs)} documents after reranking")

            # Update state with combined output
            state = update_retrieval_output(
                state=state,
                refined_queries=refined_queries,
                retrieved_docs=retrieved_docs,
                reranked_docs=reranked_docs,
                metadata=retrieval_metadata
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
                    "strategy": str(retrieval_metadata.strategy) if retrieval_metadata else "unknown"
                }
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
                error_message=str(e)
            )

            # Set empty results on failure
            state = update_retrieval_output(
                state=state,
                refined_queries=[state["query"]],
                retrieved_docs=[],
                reranked_docs=[]
            )
            return update_state_with_agent_result(state, result)

    async def handle_stream(
        self,
        state: RAGState,
        context: Optional[Dict[str, Any]] = None
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
                    "refined_queries": len(refined_queries)
                }
            }

            # Stage 2: Retrieval
            yield {"type": "stage", "data": {"stage": "retrieval", "status": "started"}}

            retrieved_docs, retrieval_metadata = await self._retrieve_documents(
                queries=refined_queries,
                user_id=user_id
            )

            yield {
                "type": "stage",
                "data": {
                    "stage": "retrieval",
                    "status": "completed",
                    "retrieved_docs": len(retrieved_docs)
                }
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
                metadata=retrieval_metadata
            )

            execution_time = (time.time() - start_time) * 1000
            result = create_agent_result(
                agent_name="RetrievalAgent",
                status=AgentStatus.COMPLETED,
                execution_time_ms=execution_time
            )
            state = update_state_with_agent_result(state, result)

            yield {
                "type": "stage",
                "data": {
                    "stage": "reranking",
                    "status": "completed",
                    "reranked_docs": len(reranked_docs)
                }
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

        return unique_queries[:self.config.expansion_count]

    def _synonym_expansion(self, query: str) -> List[str]:
        """
        Generate synonym-based query expansions.

        TODO: Enhance with WordNet or domain-specific synonym dictionaries.

        Args:
            query: Original query

        Returns:
            List of synonym-expanded queries
        """
        # Simplified Vietnamese synonym mapping
        synonym_map = {
            "hỏi": ["đặt câu hỏi", "tìm hiểu"],
            "tài liệu": ["văn bản", "hồ sơ"],
            "hợp đồng": ["thỏa thuận", "biên bản"],
            # TODO: Add more domain-specific synonyms
        }

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
        self,
        queries: List[str],
        user_id: str
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
                search_time_ms=0
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
                enable_rerank=self.config.enable_reranking
            )

            # Convert to DocumentWithScore objects
            retrieved_docs = []
            for result in search_results:
                doc = DocumentWithScore(
                    doc_id=result.get("document_id", result.get("chunk_id", "")),
                    content=result.get("text", result.get("content", "")),
                    filename=result.get("filename", result.get("metadata", {}).get("title", "Unknown")),
                    page_number=result.get("page_number", result.get("metadata", {}).get("page", 0)),
                    chunk_index=result.get("chunk_index", result.get("metadata", {}).get("chunk_index", 0)),
                    score=result.get("rrf_score", result.get("score", 0.0)),
                    metadata=result.get("metadata", {})
                )
                retrieved_docs.append(doc)

            search_time = (time.time() - start_time) * 1000

            metadata = RetrievalMetadata(
                strategy=RetrievalStrategy.HYBRID,
                total_results=len(retrieved_docs),
                query_expansions=queries[1:] if len(queries) > 1 else [],
                search_time_ms=search_time
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
                search_time_ms=search_time
            )

    # ==========================================================================
    # Stage 3: Reranking (merged from RerankingAgent)
    # ==========================================================================

    async def _rerank_documents(
        self,
        query: str,
        documents: List[DocumentWithScore]
    ) -> List[DocumentWithScore]:
        """
        Rerank documents using cross-encoder or content overlap.

        Merged functionality from RerankingAgent.

        TODO: Implement cross-encoder reranking with models like:
        - BAAI/bge-reranker-v2-m3
        - cross-encoder/ms-marco-MiniLM-L-6-v2

        Args:
            query: Original query
            documents: List of retrieved documents

        Returns:
            Reranked documents (top-k after filtering)
        """
        if not documents or not self.config.enable_reranking:
            return documents

        # TODO: Implement cross-encoder reranking
        # For now, use content overlap fallback
        return self._fallback_reranking(query, documents)

    def _fallback_reranking(
        self,
        query: str,
        documents: List[DocumentWithScore]
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
                metadata=doc.metadata
            )
            reranked_docs.append(reranked_doc)

        # Sort and filter
        reranked_docs.sort(key=lambda x: x.score, reverse=True)
        filtered = [d for d in reranked_docs if d.score >= self.config.rerank_threshold]

        return filtered[:self.config.rerank_top_k]
