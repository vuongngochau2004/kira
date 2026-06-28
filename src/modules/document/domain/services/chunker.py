"""Semantic text chunking with token-based sizing and overlap.

Migrated from src/ingestion/chunker.py
"""

import re
from typing import Protocol

import tiktoken

from src.config.config import settings
from src.modules.document.domain.models import Chunk
from src.modules.document.domain.constants import LEGAL_HEADING_PATTERN, CHUNKER_PAGE_MARKER_PATTERN


class TextEncoding(Protocol):
    def encode(self, text: str) -> list[int]: ...

    def decode(self, tokens: list[int]) -> str: ...


class CharacterEncodingFallback:
    """Offline fallback when tiktoken cannot load its BPE cache."""

    def encode(self, text: str) -> list[int]:
        return [ord(char) for char in text]

    def decode(self, tokens: list[int]) -> str:
        return "".join(chr(token) for token in tokens)


def _get_encoding(encoding_name: str) -> TextEncoding:
    try:
        return tiktoken.get_encoding(encoding_name)
    except Exception:
        return CharacterEncodingFallback()


def _count_tokens(text: str, encoding: TextEncoding) -> int:
    """Count tokens in text using tiktoken."""
    return len(encoding.encode(text))


def _split_text(text: str) -> list[str]:
    """Split text into paragraphs."""
    paragraphs = text.split("\n\n")
    return [p.strip() for p in paragraphs if p.strip()]


def _split_large_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    encoding: TextEncoding,
) -> list[str]:
    """Split a large text block into chunks with overlap."""
    tokens = encoding.encode(text)
    sub_chunks: list[str] = []
    start = 0

    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        sub_chunks.append(chunk_text.strip())
        start += chunk_size - chunk_overlap
    return sub_chunks


def _split_large_text_by_blocks(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    encoding: TextEncoding,
) -> list[str]:
    """Split large text on paragraph boundaries before falling back to tokens."""
    blocks = _split_text(text)
    if len(blocks) <= 1:
        return _split_large_text(text, chunk_size, chunk_overlap, encoding)

    sub_chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    for block in blocks:
        block_tokens = _count_tokens(block, encoding)

        if block_tokens > chunk_size:
            if current_parts:
                sub_chunks.append("\n\n".join(current_parts).strip())
                current_parts = []
                current_tokens = 0

            # Legal clauses and list items are atomic retrieval units. Splitting
            # a single paragraph by tokens creates fragments without a subject
            # or legal context (and makes citations misleading). Preserve the
            # boundary and allow this exceptional chunk to exceed the target.
            sub_chunks.append(block)
            continue

        if current_parts and current_tokens + block_tokens > chunk_size:
            sub_chunks.append("\n\n".join(current_parts).strip())
            current_parts = _get_overlap_parts(current_parts, chunk_overlap, encoding)
            current_tokens = sum(_count_tokens(part, encoding) for part in current_parts)

        current_parts.append(block)
        current_tokens += block_tokens

    if current_parts:
        sub_chunks.append("\n\n".join(current_parts).strip())

    return [chunk for chunk in sub_chunks if chunk]


def _get_overlap_parts(
    parts: list[str],
    chunk_overlap: int,
    encoding: TextEncoding,
) -> list[str]:
    """Get parts from the end that fit within the overlap size."""
    overlap_parts: list[str] = []
    overlap_tokens = 0

    for part in reversed(parts):
        part_tokens = _count_tokens(part, encoding)
        if overlap_tokens + part_tokens <= chunk_overlap:
            overlap_parts.insert(0, part)
            overlap_tokens += part_tokens
        else:
            break
    return overlap_parts


def _page_range(text: str) -> tuple[int | None, int | None]:
    pages = [int(match.group(1)) for match in CHUNKER_PAGE_MARKER_PATTERN.finditer(text)]
    if not pages:
        return None, None
    return min(pages), max(pages)


def _active_page_marker_before(text: str, offset: int) -> str | None:
    marker = None
    for match in CHUNKER_PAGE_MARKER_PATTERN.finditer(text, 0, offset):
        marker = match.group(0)
    return marker


def _section_label(text: str) -> tuple[str, str]:
    for line in text.splitlines():
        cleaned = line.strip().strip("*# ")
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered.startswith("điều "):
            return "article", cleaned
        if lowered.startswith("chương "):
            return "chapter", cleaned
        if lowered.startswith("phụ lục"):
            return "appendix", cleaned
    return "section", ""


def _split_legal_sections(text: str) -> list[str]:
    matches = list(LEGAL_HEADING_PATTERN.finditer(text))
    if not matches:
        return []

    sections: list[str] = []
    if matches[0].start() > 0:
        intro = text[:matches[0].start()].strip()
        if intro:
            sections.append(intro)

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[start:end].strip()
        if section:
            active_marker = _active_page_marker_before(text, start)
            if active_marker and not CHUNKER_PAGE_MARKER_PATTERN.search(section):
                section = f"{active_marker}\n{section}"
            elif active_marker and not section.startswith(active_marker):
                first_marker = CHUNKER_PAGE_MARKER_PATTERN.search(section)
                if first_marker and first_marker.start() > 0:
                    section = f"{active_marker}\n{section}"
            sections.append(section)

    return sections


def _chunk_legal_document(
    text: str,
    document_id: str,
    chunk_size: int,
    chunk_overlap: int,
    encoding: TextEncoding,
) -> list[Chunk]:
    sections = _split_legal_sections(text)
    chunks: list[Chunk] = []

    for section in sections:
        section_type, label = _section_label(section)
        page_start, page_end = _page_range(section)
        metadata = {
            "document_id": document_id,
            "chunking_strategy": "legal_structure",
            "section_type": section_type,
        }
        if label:
            metadata["section_label"] = label
        if page_start is not None:
            metadata["page_start"] = page_start
            metadata["page_end"] = page_end

        token_count = _count_tokens(section, encoding)
        if token_count <= chunk_size:
            chunks.append(
                Chunk(
                    index=len(chunks),
                    content=section,
                    token_count=token_count,
                    metadata=metadata,
                )
            )
            continue

        sub_chunks = _split_large_text_by_blocks(section, chunk_size, chunk_overlap, encoding)
        for sub_index, sub in enumerate(sub_chunks):
            sub_metadata = metadata.copy()
            sub_metadata["section_part"] = sub_index + 1
            sub_page_start, sub_page_end = _page_range(sub)
            if sub_page_start is not None:
                sub_metadata["page_start"] = sub_page_start
                sub_metadata["page_end"] = sub_page_end
            chunks.append(
                Chunk(
                    index=len(chunks),
                    content=sub,
                    token_count=_count_tokens(sub, encoding),
                    metadata=sub_metadata,
                )
            )

    return chunks


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

    encoding = _get_encoding(encoding_name)

    if settings.legal_chunking_enabled:
        legal_chunks = _chunk_legal_document(
            text=text,
            document_id=document_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            encoding=encoding,
        )
        if legal_chunks:
            return legal_chunks

    paragraphs = _split_text(text)
    chunks: list[Chunk] = []
    current_parts: list[str] = []
    current_tokens = 0

    # Base metadata to include in all chunks
    base_metadata = {"document_id": document_id}
    if page_number is not None:
        base_metadata["page_number"] = page_number

    for paragraph in paragraphs:
        para_tokens = _count_tokens(paragraph, encoding)

        if para_tokens > chunk_size:
            if current_parts:
                chunk_text = "\n\n".join(current_parts)
                chunks.append(Chunk(
                    index=len(chunks),
                    content=chunk_text,
                    token_count=_count_tokens(chunk_text, encoding),
                    metadata=base_metadata.copy(),
                ))
                current_parts = []
                current_tokens = 0

            sub_chunks = _split_large_text(paragraph, chunk_size, chunk_overlap, encoding)
            for sub in sub_chunks:
                chunks.append(Chunk(
                    index=len(chunks),
                    content=sub,
                    token_count=_count_tokens(sub, encoding),
                    metadata=base_metadata.copy(),
                ))
            continue

        if current_tokens + para_tokens > chunk_size and current_parts:
            chunk_text = "\n\n".join(current_parts)
            chunks.append(Chunk(
                index=len(chunks),
                content=chunk_text,
                token_count=_count_tokens(chunk_text, encoding),
                metadata=base_metadata.copy(),
            ))

            overlap_parts = _get_overlap_parts(current_parts, chunk_overlap, encoding)
            current_parts = overlap_parts
            current_tokens = sum(_count_tokens(p, encoding) for p in current_parts)

        current_parts.append(paragraph)
        current_tokens += para_tokens

    if current_parts:
        chunk_text = "\n\n".join(current_parts)
        chunks.append(Chunk(
            index=len(chunks),
            content=chunk_text,
            token_count=_count_tokens(chunk_text, encoding),
            metadata=base_metadata.copy(),
        ))

    return chunks


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count tokens in text.

    Args:
        text: Text to count
        encoding_name: tiktoken encoding name

    Returns:
        Token count
    """
    encoding = tiktoken.get_encoding(encoding_name)
    return _count_tokens(text, encoding)


__all__ = ["Chunk", "chunk_document", "count_tokens"]
