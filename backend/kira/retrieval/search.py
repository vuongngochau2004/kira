"""Search entry point used by chat and drafting: hybrid dense + BM25 search over a user's documents."""

import logging
from typing import Any
from uuid import UUID

from kira.documents.repository import (
    completed_chunks_signature_for_user,
    get_documents_batch,
    list_completed_chunks_for_user,
)
from kira.providers.vector_store import QdrantVectorStore
from kira.retrieval.bm25 import BM25IndexManager
from kira.retrieval.hybrid_search import (
    hybrid_search,
    hybrid_search_candidates,
)


class BM25KeywordSearchAdapter:
    """Expose the in-memory BM25 manager through the retrieval application port."""

    def __init__(self, manager: BM25IndexManager):
        self._manager = manager

    def has_documents(self, user_id: str) -> bool:
        return self._manager.has_documents(user_id)

    def get_index(self, user_id: str) -> Any:
        return self._manager.get_index(user_id)

    def get_signature(self, user_id: str) -> Any:
        return self._manager.get_signature(user_id)

    def rebuild_from_chunks(
        self, user_id: str, chunks: list[dict[str, Any]], signature: Any = None
    ) -> None:
        self._manager.rebuild_from_chunks(user_id=user_id, all_chunks=chunks, signature=signature)


class PostgresRetrievalDocumentAdapter:
    """Expose Postgres retrieval metadata through the retrieval application port."""

    async def list_completed_chunks(self, user_id: UUID) -> list[dict[str, Any]]:
        return await list_completed_chunks_for_user(user_id)

    async def completed_chunks_signature(self, user_id: UUID) -> Any:
        return await completed_chunks_signature_for_user(user_id)

    async def get_filenames(self, document_ids: list[str]) -> dict[str, str]:
        return await get_documents_batch(document_ids)


logger = logging.getLogger(__name__)


class SearchUseCase:
    """Use case for search operations.

    Orchestrates retrieval by combining:
    - Dense vector search (Qdrant)
    - BM25 keyword search
    - RRF fusion
    - Configured reranking adapter
    """

    def __init__(
        self,
        vector_store: QdrantVectorStore,
        keyword_search: BM25KeywordSearchAdapter | None = None,
        documents: PostgresRetrievalDocumentAdapter | None = None,
        llm_client=None,
    ):
        """Initialize search use case.

        Args:
            vector_store: Vector store port for dense retrieval
            keyword_search: Port for user-scoped BM25 index access
            documents: Port for persisted chunks and document filenames
            llm_client: Optional LLM client for reranking
        """
        self._vector_store = vector_store
        self._keyword_search = keyword_search
        self._documents = documents
        self._llm_client = llm_client

    async def execute(
        self,
        query_embedding: list[float],
        query_text: str,
        user_id: str | None = None,
        k: int = 5,
        rrf_k: int = 60,
    ) -> list[dict]:
        """Execute hybrid search with the configured reranking adapter.

        Args:
            query_embedding: Query vector for dense search
            query_text: Query text for BM25 search
            user_id: Optional user ID filter
            k: Number of final results
            rrf_k: RRF constant

        Returns:
            Reranked search results
        """
        # Get BM25 index for user
        bm25_index = None
        if self._keyword_search is not None and user_id is not None:
            await self._ensure_bm25_index(user_id)
            bm25_index = self._keyword_search.get_index(user_id)

        # Execute hybrid search
        results = await hybrid_search(
            query_embedding=query_embedding,
            query_text=query_text,
            user_id=user_id,
            bm25_index=bm25_index,
            k=k,
            rrf_k=rrf_k,
            llm_client=self._llm_client,
            dense_search_fn=self._dense_search,
        )
        await self._resolve_filenames(results)
        return results

    async def execute_candidates(
        self,
        query_embedding: list[float],
        query_text: str,
        user_id: str | None = None,
        k: int = 20,
        rrf_k: int = 60,
    ) -> list[dict]:
        """Return the candidate pool for the RAG LLM reranking stage."""
        bm25_index = None
        if self._keyword_search is not None and user_id is not None:
            await self._ensure_bm25_index(user_id)
            bm25_index = self._keyword_search.get_index(user_id)

        results = await hybrid_search_candidates(
            query_embedding=query_embedding,
            query_text=query_text,
            user_id=user_id,
            bm25_index=bm25_index,
            k=k,
            rrf_k=rrf_k,
            dense_search_fn=self._dense_search,
        )
        await self._resolve_filenames(results)
        return results

    async def _resolve_filenames(self, results: list[dict]) -> None:
        """Enrich results with source filenames from the document repository."""
        # Resolve filenames from PostgreSQL database to replace "Unknown" values
        doc_ids = list(
            {
                str(r.get("document_id") or (r.get("metadata") or {}).get("document_id"))
                for r in results
                if r.get("document_id") or (r.get("metadata") or {}).get("document_id")
            }
        )
        if doc_ids and self._documents is not None:
            try:
                logger.info(f"[SearchUseCase] Resolving filenames for doc_ids: {doc_ids}")
                doc_mapping = await self._documents.get_filenames(doc_ids)
                logger.info(f"[SearchUseCase] doc_mapping resolved to: {doc_mapping}")
                for r in results:
                    doc_id = str(
                        r.get("document_id") or (r.get("metadata") or {}).get("document_id") or ""
                    )
                    if doc_id in doc_mapping:
                        filename = doc_mapping[doc_id]
                        r["filename"] = filename
                        if "metadata" in r and isinstance(r["metadata"], dict):
                            r["metadata"]["title"] = filename
                            r["metadata"]["filename"] = filename
            except Exception as e:
                logger.error(
                    f"Failed to resolve search result filenames in SearchUseCase: {e}",
                    exc_info=True,
                )

    async def _ensure_bm25_index(self, user_id: str) -> None:
        """Keep the in-memory BM25 index in sync with the user's persisted chunks.

        Documents are chunked by the Celery worker in another process, so this process never
        sees their in-memory index updates. Compare a cheap DB fingerprint of the completed
        chunk set with the one the index was built from, and rebuild when they differ
        (new, reprocessed or deleted documents) or when the index is empty.
        """
        if self._keyword_search is None or self._documents is None:
            return

        try:
            user_uuid = UUID(str(user_id))
        except ValueError:
            logger.warning("Skipping BM25 lazy rebuild for invalid user_id=%s", user_id)
            return

        signature = await self._documents.completed_chunks_signature(user_uuid)
        # The manager drops the signature whenever the index is cleared, so a fresh, emptied
        # or never-built index always mismatches and gets rebuilt.
        if self._keyword_search.get_signature(user_id) == signature:
            return

        logger.info(
            "BM25 index out of date for user=%s; rebuilding from persisted chunks (signature=%s)",
            user_id,
            signature,
        )
        chunks = await self._documents.list_completed_chunks(user_uuid)
        self._keyword_search.rebuild_from_chunks(
            user_id=user_id, chunks=chunks, signature=signature
        )
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
