"""Search use case for retrieval operations.

Orchestrates hybrid search combining dense and BM25 retrieval with RRF fusion.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from src.modules.retrieval.domain.services.hybrid_search import hybrid_search
from src.modules.retrieval.infrastructure.keyword.bm25_manager import BM25IndexManager
from src.shared.ports.vector_store import VectorStorePort

logger = logging.getLogger(__name__)

BM25RebuildLoader = Callable[[UUID], Awaitable[list[dict[str, Any]]]]


class SearchUseCase:
    """Use case for search operations.

    Orchestrates retrieval by combining:
    - Dense vector search (Qdrant)
    - BM25 keyword search
    - RRF fusion
    - Optional LLM reranking
    """

    def __init__(
        self,
        vector_store: VectorStorePort,
        bm25_index_getter=None,
        bm25_manager: BM25IndexManager | None = None,
        bm25_rebuild_loader: BM25RebuildLoader | None = None,
        llm_client=None,
    ):
        """Initialize search use case.

        Args:
            vector_store: Vector store port for dense retrieval
            bm25_index_getter: Function to get BM25 index for user
            bm25_manager: BM25 manager for lazy rebuild checks
            bm25_rebuild_loader: Function that loads persisted chunks for a user
            llm_client: Optional LLM client for reranking
        """
        self._vector_store = vector_store
        self._get_bm25_index = bm25_index_getter
        self._bm25_manager = bm25_manager
        self._bm25_rebuild_loader = bm25_rebuild_loader
        self._llm_client = llm_client

        # Set LLM client for reranking in hybrid_search
        if llm_client is not None:
            from src.modules.retrieval.domain.services.hybrid_search import set_llm_client
            set_llm_client(llm_client)

    async def execute(
        self,
        query_embedding: list[float],
        query_text: str,
        user_id: str | None = None,
        k: int = 5,
        rrf_k: int = 60,
        enable_rerank: bool = False,
    ) -> list[dict]:
        """Execute hybrid search.

        Args:
            query_embedding: Query vector for dense search
            query_text: Query text for BM25 search
            user_id: Optional user ID filter
            k: Number of final results
            rrf_k: RRF constant
            enable_rerank: Enable LLM reranking

        Returns:
            Fused list of chunks ranked by RRF score (and reranked if enabled)
        """
        # Get BM25 index for user
        bm25_index = None
        if self._get_bm25_index is not None and user_id is not None:
            await self._ensure_bm25_index(user_id)
            bm25_index = self._get_bm25_index(user_id)

        # Execute hybrid search
        results = await hybrid_search(
            query_embedding=query_embedding,
            query_text=query_text,
            user_id=user_id,
            bm25_index=bm25_index,
            k=k,
            rrf_k=rrf_k,
            enable_rerank=enable_rerank,
            dense_search_fn=self._dense_search,
        )

        # Resolve filenames from PostgreSQL database to replace "Unknown" values
        doc_ids = list(
            {
                str(r.get("document_id") or (r.get("metadata") or {}).get("document_id"))
                for r in results
                if r.get("document_id") or (r.get("metadata") or {}).get("document_id")
            }
        )
        if doc_ids:
            try:
                logger.info(f"[SearchUseCase] Resolving filenames for doc_ids: {doc_ids}")
                from src.modules.retrieval.infrastructure.document_store.document_repository import get_documents_batch
                doc_mapping = await get_documents_batch(doc_ids)
                logger.info(f"[SearchUseCase] doc_mapping resolved to: {doc_mapping}")
                for r in results:
                    doc_id = str(r.get("document_id") or (r.get("metadata") or {}).get("document_id") or "")
                    if doc_id in doc_mapping:
                        filename = doc_mapping[doc_id]
                        r["filename"] = filename
                        if "metadata" in r and isinstance(r["metadata"], dict):
                            r["metadata"]["title"] = filename
                            r["metadata"]["filename"] = filename
            except Exception as e:
                logger.error(f"Failed to resolve search result filenames in SearchUseCase: {e}", exc_info=True)

        return results

    async def _ensure_bm25_index(self, user_id: str) -> None:
        """Rebuild an empty in-memory BM25 index from persisted chunks."""
        if self._bm25_manager is None or self._bm25_rebuild_loader is None:
            return

        if self._bm25_manager.has_documents(user_id):
            return

        try:
            user_uuid = UUID(str(user_id))
        except ValueError:
            logger.warning("Skipping BM25 lazy rebuild for invalid user_id=%s", user_id)
            return

        logger.info("BM25 index empty for user=%s; rebuilding from persisted chunks", user_id)
        chunks = await self._bm25_rebuild_loader(user_uuid)

        if not chunks:
            logger.info("BM25 rebuild skipped for user=%s; no persisted chunks found", user_id)
            return

        self._bm25_manager.rebuild_from_chunks(user_id=user_id, all_chunks=chunks)
        logger.info("BM25 rebuild completed for user=%s; chunks=%d", user_id, len(chunks))

    async def _dense_search(
        self,
        query_embedding: list[float],
        user_id: str | None = None,
        k: int = 5,
    ) -> list[dict]:
        """Run dense retrieval through the vector store port."""
        results = await self._vector_store.search(
            embedding=query_embedding,
            user_id=user_id,
            k=k,
        )
        return [
            {
                "id": result.id,
                "text": result.text,
                "content": result.text,
                "metadata": result.metadata,
                "document_id": result.metadata.get("document_id"),
                "chunk_index": result.metadata.get("chunk_index"),
                "page_number": result.metadata.get("page_number"),
                "score": result.score,
            }
            for result in results
        ]


__all__ = ["SearchUseCase"]
