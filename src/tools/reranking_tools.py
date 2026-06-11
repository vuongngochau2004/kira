"""
# DEPRECATED: This file has been migrated to modules/retrieval/domain/services/reranking-service.py

This file is a backward-compatible shim and will be removed in Phase 10.
Please update your imports:

OLD:
    from src.tools.reranking_tools import llm_rerank, score_and_rerank, init_reranking_tools

NEW:
    from modules.retrieval.domain.services.reranking_service import llm_rerank, score_and_rerank, init_reranking_service
"""

# Backward-compatible re-exports
from src.modules.retrieval.domain.services.reranking_service import (
    init_reranking_service as init_reranking_tools,  # Alias for backward compatibility
    llm_rerank,
    score_and_rerank,
)

__all__ = [
    "init_reranking_tools",
    "llm_rerank",
    "score_and_rerank",
]
