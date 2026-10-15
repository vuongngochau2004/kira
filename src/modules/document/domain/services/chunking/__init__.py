"""Document chunking strategies package.

This package contains ONLY chunking strategies:
- recursive.py: Paragraph & token chunker with overlap
- legal.py: Legal structure-aware chunker (Chương/Điều/Khoản/Phụ lục)
"""

from src.modules.document.domain.models import Chunk
from src.modules.document.domain.services.chunking.legal import (
    chunk_legal_document,
    split_legal_sections,
)
from src.modules.document.domain.services.chunking.recursive import (
    chunk_recursive,
    split_large_text,
    split_large_text_by_blocks,
    split_text,
)

__all__ = [
    "Chunk",
    "chunk_recursive",
    "chunk_legal_document",
    "split_legal_sections",
    "split_text",
    "split_large_text",
    "split_large_text_by_blocks",
]
