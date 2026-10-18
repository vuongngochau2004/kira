"""Reranking service facade and LangChain tools for agentic RAG workflows."""

import asyncio
import json
import logging
from typing import Any

from langchain_core.tools import tool

from src.modules.retrieval.domain.services.reranking.llm_reranker import (
    format_documents_for_reranking,
    parse_reranking_response,
    reorder_by_indices,
    rerank_documents_with_llm,
    run_llm_rerank,
)
from src.modules.retrieval.domain.services.reranking.scoring_reranker import (
    score_all_documents_async,
    score_and_filter_documents,
    score_document_async,
)

logger = logging.getLogger(__name__)

# Global LLM client reference
_llm_client: Any = None


def init_reranking_service(llm_client: Any = None) -> None:
    """Initialize global LLM client for reranking service.

    Args:
        llm_client: LLM client instance with chat_async method
    """
    global _llm_client
    _llm_client = llm_client


def get_llm_client() -> Any:
    """Get the global LLM client instance."""
    return _llm_client


def set_llm_client(llm_client: Any) -> None:
    """Set the global LLM client instance."""
    global _llm_client
    _llm_client = llm_client


@tool
def llm_rerank(
    query: str,
    documents: str,
    top_k: int = 5,
) -> str:
    """Rerank documents using LLM to improve relevance.

    Use this tool AFTER initial retrieval to improve precision.
    The LLM analyzes the query and each document to determine
    which documents are most relevant.

    Args:
        query: The user's search query
        documents: JSON string of retrieved documents to rerank.
        top_k: Number of top documents to return after reranking

    Returns:
        JSON string of reranked documents with updated order
    """
    try:
        doc_list = json.loads(documents)
        if not doc_list:
            return json.dumps([], ensure_ascii=False)

        if _llm_client is None:
            logger.warning("LLM client not initialized, returning original order")
            return json.dumps(doc_list[:top_k], ensure_ascii=False)

        reranked = asyncio.run(
            rerank_documents_with_llm(
                query=query,
                candidates=doc_list,
                llm_client=_llm_client,
                top_k=top_k,
            )
        )
        return json.dumps(reranked[:top_k], ensure_ascii=False)

    except Exception as e:
        logger.error("Error in llm_rerank: %s", e, exc_info=True)
        try:
            doc_list = json.loads(documents)
            return json.dumps(doc_list[:top_k], ensure_ascii=False)
        except (TypeError, ValueError, json.JSONDecodeError):
            return json.dumps([], ensure_ascii=False)


@tool
def score_and_rerank(
    query: str,
    documents: str,
    top_k: int = 5,
    min_score_threshold: float = 0.3,
) -> str:
    """Score documents individually and rerank by relevance score.

    Args:
        query: The user's search query
        documents: JSON string of retrieved documents to score
        top_k: Number of top documents to return
        min_score_threshold: Minimum relevance score (0-1) to keep

    Returns:
        JSON string of scored and reranked documents
    """
    try:
        doc_list = json.loads(documents)
        if not doc_list:
            return json.dumps([], ensure_ascii=False)

        if _llm_client is None:
            logger.warning("LLM client not initialized, returning original order")
            return json.dumps(doc_list[:top_k], ensure_ascii=False)

        reranked = asyncio.run(
            score_and_filter_documents(
                query=query,
                candidates=doc_list,
                llm_client=_llm_client,
                top_k=top_k,
                min_score_threshold=min_score_threshold,
            )
        )
        return json.dumps(reranked[:top_k], ensure_ascii=False)

    except Exception as e:
        logger.error("Error in score_and_rerank: %s", e, exc_info=True)
        try:
            doc_list = json.loads(documents)
            return json.dumps(doc_list[:top_k], ensure_ascii=False)
        except (TypeError, ValueError, json.JSONDecodeError):
            return json.dumps([], ensure_ascii=False)


@tool
def tei_rerank(
    query: str,
    documents: str,
    top_k: int = 5,
) -> str:
    """Rerank documents using TEI Cross-Encoder service (BAAI/bge-reranker-v2-m3).

    Args:
        query: The user's search query
        documents: JSON string of retrieved documents to rerank
        top_k: Number of top documents to return

    Returns:
        JSON string of cross-encoder reranked documents
    """
    try:
        from src.modules.retrieval.domain.services.reranking.tei_reranker import (
            rerank_documents_with_tei,
        )

        doc_list = json.loads(documents)
        if not doc_list:
            return json.dumps([], ensure_ascii=False)

        reranked = asyncio.run(
            rerank_documents_with_tei(
                query=query,
                candidates=doc_list,
                top_k=top_k,
            )
        )
        return json.dumps(reranked[:top_k], ensure_ascii=False)

    except Exception as e:
        logger.error("Error in tei_rerank: %s", e, exc_info=True)
        try:
            doc_list = json.loads(documents)
            return json.dumps(doc_list[:top_k], ensure_ascii=False)
        except (TypeError, ValueError, json.JSONDecodeError):
            return json.dumps([], ensure_ascii=False)


# Backward-compatible private aliases
_run_llm_rerank = run_llm_rerank
_format_documents_for_reranking = format_documents_for_reranking
_parse_reranking_response = parse_reranking_response
_reorder_by_indices = reorder_by_indices
_score_document_async = score_document_async
_score_all_documents_async = score_all_documents_async
_get_llm_client = get_llm_client

__all__ = [
    "init_reranking_service",
    "set_llm_client",
    "get_llm_client",
    "llm_rerank",
    "score_and_rerank",
    "tei_rerank",
    # Underlying functions
    "rerank_documents_with_llm",
    "score_and_filter_documents",
    # Legacy private symbols
    "_run_llm_rerank",
    "_score_document_async",
    "_score_all_documents_async",
    "_format_documents_for_reranking",
    "_parse_reranking_response",
    "_reorder_by_indices",
    "_get_llm_client",
]
