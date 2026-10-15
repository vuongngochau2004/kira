"""Domain services for retrieval module.

Contains core business logic for BM25 keyword search, Reciprocal Rank Fusion,
hybrid retrieval, and LLM reranking strategies.
"""

from src.modules.retrieval.domain.services.bm25 import (
    BM25Index,
    _normalize,
    _tokenize,
    normalize_text,
    tokenize_text,
)
from src.modules.retrieval.domain.services.fusion import (
    DEFAULT_RRF_K,
    _build_sorted_results,
    _make_doc_key,
    build_sorted_results,
    make_doc_key,
    reciprocal_rank_fusion,
)
from src.modules.retrieval.domain.services.hybrid_search import (
    DENSE_MULTIPLIER,
    format_dense_results,
    get_bm25_results,
    hybrid_search,
    set_llm_client,
)
from src.modules.retrieval.domain.services.reranking import (
    format_documents_for_reranking,
    parse_reranking_response,
    reorder_by_indices,
    rerank_documents_with_llm,
    run_llm_rerank,
    score_all_documents_async,
    score_and_filter_documents,
    score_document_async,
)
from src.modules.retrieval.domain.services.reranking_service import (
    init_reranking_service,
    llm_rerank,
    score_and_rerank,
)

__all__ = [
    # Fusion
    "DEFAULT_RRF_K",
    "reciprocal_rank_fusion",
    "make_doc_key",
    "build_sorted_results",
    "_make_doc_key",
    "_build_sorted_results",
    # Hybrid search
    "DENSE_MULTIPLIER",
    "hybrid_search",
    "format_dense_results",
    "get_bm25_results",
    "set_llm_client",
    # Reranking strategies & tools
    "init_reranking_service",
    "llm_rerank",
    "score_and_rerank",
    "rerank_documents_with_llm",
    "score_and_filter_documents",
    "run_llm_rerank",
    "score_document_async",
    "score_all_documents_async",
    "format_documents_for_reranking",
    "parse_reranking_response",
    "reorder_by_indices",
    # BM25
    "BM25Index",
    "normalize_text",
    "tokenize_text",
    "_tokenize",
    "_normalize",
]
