"""BM25 index facade for backward compatibility.

All BM25 logic has been consolidated into bm25.py.
"""

from src.modules.retrieval.domain.services.bm25 import (
    BM25Index,
    _normalize,
    _tokenize,
    normalize_text,
    tokenize_text,
)

__all__ = [
    "BM25Index",
    "normalize_text",
    "tokenize_text",
    "_tokenize",
    "_normalize",
]
