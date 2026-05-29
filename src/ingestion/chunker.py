"""Semantic text chunking with token-based sizing and overlap."""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import tiktoken

from config.config import settings


@dataclass
class Chunk:
    """A chunk of text from a document."""
    index: int
    content: str
    token_count: int
    metadata: dict = field(default_factory=dict)


def _count_tokens(text: str, encoding) -> int:
    """Count tokens in text using tiktoken."""
    return len(encoding.encode(text))


def _split_text(text: str) -> list[str]:
    """Split text into paragraphs."""
    paragraphs = text.split("\n\n")
    return [p.strip() for p in paragraphs if p.strip()]


def _split_large_text(text: str, chunk_size: int, chunk_overlap: int, encoding) -> list[str]:
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


def _get_overlap_parts(parts: list[str], chunk_overlap: int, encoding) -> list[str]:
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


def chunk_document(
    text: str,
    document_id: str = "",
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    encoding_name: str = "cl100k_base",
) -> list[Chunk]:
    """Split document text into semantic chunks.

    Args:
        text: Full document text.
        document_id: Optional doc ID for metadata.
        chunk_size: Target chunk size in tokens.
        chunk_overlap: Overlap between chunks in tokens.
        encoding_name: tiktoken encoding (default: cl100k_base).

    Returns:
        List of Chunk objects.
    """
    if not text.strip():
        return []

    if chunk_size is None:
        chunk_size = settings.chunk_size
    if chunk_overlap is None:
        chunk_overlap = settings.chunk_overlap

    encoding = tiktoken.get_encoding(encoding_name)
    paragraphs = _split_text(text)
    chunks: list[Chunk] = []
    current_parts: list[str] = []
    current_tokens = 0

    for paragraph in paragraphs:
        para_tokens = _count_tokens(paragraph, encoding)

        if para_tokens > chunk_size:
            if current_parts:
                chunk_text = "\n\n".join(current_parts)
                chunks.append(Chunk(
                    index=len(chunks),
                    content=chunk_text,
                    token_count=_count_tokens(chunk_text, encoding),
                    metadata={"document_id": document_id},
                ))
                current_parts = []
                current_tokens = 0

            sub_chunks = _split_large_text(paragraph, chunk_size, chunk_overlap, encoding)
            for sub in sub_chunks:
                chunks.append(Chunk(
                    index=len(chunks),
                    content=sub,
                    token_count=_count_tokens(sub, encoding),
                    metadata={"document_id": document_id},
                ))
            continue

        if current_tokens + para_tokens > chunk_size and current_parts:
            chunk_text = "\n\n".join(current_parts)
            chunks.append(Chunk(
                index=len(chunks),
                content=chunk_text,
                token_count=_count_tokens(chunk_text, encoding),
                metadata={"document_id": document_id},
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
            metadata={"document_id": document_id},
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
