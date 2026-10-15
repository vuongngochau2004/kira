"""Document chunking coordinator and facade.

Dispatches chunking requests according to document type and configuration:
- legal.py: Legal structure chunking for administrative documents
- recursive.py: Paragraph and token chunking with overlap
- token_counter.py: Tiktoken BPE token counting with offline fallback
"""

from src.config.config import settings
from src.modules.document.domain.models import Chunk
from src.modules.document.domain.services.chunking.legal import (
    chunk_legal_document,
    extract_section_label,
    get_active_page_marker_before,
    get_page_range,
    split_legal_sections,
)
from src.modules.document.domain.services.chunking.recursive import (
    chunk_recursive,
    get_overlap_parts,
    split_large_text,
    split_large_text_by_blocks,
    split_text,
)
from src.modules.document.domain.services.token_counter import (
    _count_tokens,
    _get_encoding,
    count_tokens,
    get_encoding,
)


def chunk_document(
    text: str,
    document_id: str = "",
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    encoding_name: str = "cl100k_base",
    page_number: int | None = None,
) -> list[Chunk]:
    """Split document text into semantic chunks.

    Args:
        text: Full document text.
        document_id: Optional doc ID for metadata.
        chunk_size: Target chunk size in tokens.
        chunk_overlap: Overlap between chunks in tokens.
        encoding_name: tiktoken encoding (default: cl100k_base).
        page_number: Optional page number for this text (used in citations).

    Returns:
        List of Chunk objects.
    """
    if not text.strip():
        return []

    if chunk_size is None:
        chunk_size = settings.chunk_size
    if chunk_overlap is None:
        chunk_overlap = settings.chunk_overlap

    encoding = get_encoding(encoding_name)

    if settings.legal_chunking_enabled:
        legal_chunks = chunk_legal_document(
            text=text,
            document_id=document_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            encoding=encoding,
        )
        if legal_chunks:
            return legal_chunks

    return chunk_recursive(
        text=text,
        document_id=document_id,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        encoding=encoding,
        page_number=page_number,
    )


# Backward compatibility private aliases
_split_text = split_text
_split_large_text = split_large_text
_split_large_text_by_blocks = split_large_text_by_blocks
_get_overlap_parts = get_overlap_parts
_page_range = get_page_range
_active_page_marker_before = get_active_page_marker_before
_section_label = extract_section_label
_split_legal_sections = split_legal_sections
_chunk_legal_document = chunk_legal_document

__all__ = [
    "Chunk",
    "chunk_document",
    "count_tokens",
    # Legacy private symbols preserved for test compatibility
    "_get_encoding",
    "_count_tokens",
    "_split_text",
    "_split_large_text",
    "_split_large_text_by_blocks",
    "_get_overlap_parts",
    "_page_range",
    "_active_page_marker_before",
    "_section_label",
    "_split_legal_sections",
    "_chunk_legal_document",
]
