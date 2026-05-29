"""Retrieval tools for LangChain agent integration."""

import json
import sys
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.config import settings

# Global store/index references (to be set by application initialization)
_qdrant_store: Any = None
_bm25_index: Any = None
_embedding_fn: Any = None


def init_retrieval_tools(
    qdrant_store: Any = None,
    bm25_index: Any = None,
    embedding_fn: Any = None,
) -> None:
    """Initialize global retrieval dependencies.

    Args:
        qdrant_store: Qdrant/vector store instance
        bm25_index: BM25 index instance (optional)
        embedding_fn: Embedding function for query encoding (optional)
    """
    global _qdrant_store, _bm25_index, _embedding_fn
    _qdrant_store = qdrant_store
    _bm25_index = bm25_index
    _embedding_fn = embedding_fn


def _get_store() -> Any:
    """Get the global vector store instance.

    Raises:
        RuntimeError: If store has not been initialized
    """
    if _qdrant_store is None:
        raise RuntimeError("Vector store not initialized. Call init_retrieval_tools() first.")
    return _qdrant_store


def _get_bm25_index() -> Any:
    """Get the global BM25 index instance.

    Returns:
        BM25 index or None if not initialized
    """
    return _bm25_index


def _get_embedding_fn() -> Any:
    """Get the global embedding function.

    Raises:
        RuntimeError: If embedding function has not been initialized
    """
    if _embedding_fn is None:
        raise RuntimeError("Embedding function not initialized. Call init_retrieval_tools() first.")
    return _embedding_fn


def _doc_to_dict(doc: dict) -> dict:
    """Normalize document to dict for JSON serialization.

    Args:
        doc: Document dict with various field names

    Returns:
        Normalized document dict
    """
    return {
        "text": doc.get("text", doc.get("content", "")),
        "content": doc.get("text", doc.get("content", "")),
        "metadata": doc.get("metadata", {}),
        "document_id": doc.get("document_id"),
        "chunk_index": doc.get("chunk_index"),
        "score": doc.get("score", 0.0),
    }


@tool
def dense_retrieve(
    query: str,
    k: int = 5,
    user_id: str | None = None,
) -> str:
    """Retrieve documents using dense vector similarity search.

    Use this for semantic search when you need documents
    similar in meaning to the query, regardless of exact keywords.

    Args:
        query: The search query text
        k: Number of documents to retrieve
        user_id: Optional user ID for filtering results

    Returns:
        JSON string of retrieved documents with content and metadata
    """
    from src.indexing.qdrant_store import search_similar
    from src.ingestion.embedding import embed_single

    # Generate query embedding
    query_embedding = embed_single(query)

    # Search using vector store
    docs = search_similar(
        query_embedding=query_embedding,
        user_id=user_id,
        limit=k,
    )

    return json.dumps([_doc_to_dict(d) for d in docs], ensure_ascii=False)


@tool
def bm25_retrieve(
    query: str,
    k: int = 5,
) -> str:
    """Retrieve documents using BM25 keyword-based search.

    Use this for queries with specific terms, names, or keywords
    that must appear in the documents.

    Args:
        query: The search query text
        k: Number of documents to retrieve

    Returns:
        JSON string of retrieved documents with content and metadata

    Raises:
        RuntimeError: If BM25 index is not available
    """
    bm25_index = _get_bm25_index()
    if bm25_index is None:
        raise RuntimeError("BM25 index not available. Initialize with init_retrieval_tools().")

    docs = bm25_index.search(query, k=k)

    # Normalize format
    normalized = []
    for doc in docs:
        normalized.append({
            "text": doc.get("content", ""),
            "content": doc.get("content", ""),
            "metadata": doc.get("metadata", {}),
            "score": doc.get("score", 0.0),
        })

    return json.dumps(normalized, ensure_ascii=False)


@tool
def hybrid_retrieve(
    query: str,
    k: int = 5,
    rrf_k: int = 60,
    user_id: str | None = None,
) -> str:
    """Retrieve documents using hybrid search (dense + BM25 with RRF).

    Combines semantic and keyword search using Reciprocal Rank Fusion.
    Use this when you want both semantic meaning and keyword matching.

    Args:
        query: The search query text
        k: Number of documents to retrieve
        rrf_k: RRF smoothing constant (higher = more balanced ranking)
        user_id: Optional user ID for filtering results

    Returns:
        JSON string of retrieved documents with RRF scores

    Raises:
        RuntimeError: If BM25 index is not available (falls back to dense only)
    """
    from src.indexing.qdrant_store import search_similar
    from src.ingestion.embedding import embed_single
    from src.retrieval.hybrid import reciprocal_rank_fusion

    # Generate query embedding
    query_embedding = embed_single(query)

    # Get dense results
    dense_results = search_similar(
        query_embedding=query_embedding,
        user_id=user_id,
        limit=k * 2,
    )

    # Get BM25 results if available
    bm25_results = []
    bm25_index = _get_bm25_index()
    if bm25_index:
        bm25_docs = bm25_index.search(query, k=k * 2)
        for doc in bm25_docs:
            bm25_results.append({
                "text": doc.get("content", ""),
                "content": doc.get("content", ""),
                "metadata": doc.get("metadata", {}),
                "score": doc.get("score", 0),
                "document_id": doc.get("metadata", {}).get("document_id"),
                "chunk_index": doc.get("metadata", {}).get("chunk_index"),
            })

    # If no BM25, fall back to dense only
    if not bm25_results:
        return json.dumps([_doc_to_dict(d) for d in dense_results[:k]], ensure_ascii=False)

    # Normalize dense results format for fusion
    dense_formatted = []
    for item in dense_results:
        dense_formatted.append({
            "text": item.get("text", ""),
            "content": item.get("text", ""),
            "metadata": {
                "document_id": item.get("document_id"),
                "user_id": item.get("user_id"),
                "chunk_index": item.get("chunk_index"),
            },
            "score": item.get("score", 0),
            "document_id": item.get("document_id"),
            "chunk_index": item.get("chunk_index"),
        })

    # Fuse with RRF
    fused = reciprocal_rank_fusion([dense_formatted, bm25_results], k=rrf_k)

    return json.dumps(fused[:k], ensure_ascii=False)


__all__ = [
    "init_retrieval_tools",
    "dense_retrieve",
    "bm25_retrieve",
    "hybrid_retrieve",
]
