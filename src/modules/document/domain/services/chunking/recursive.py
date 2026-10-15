"""Recursive and paragraph-aware token text chunking."""

from src.modules.document.domain.models import Chunk
from src.modules.document.domain.services.token_counter import (
    TextEncoding,
    count_tokens,
)


def split_text(text: str) -> list[str]:
    """Split text into paragraphs."""
    paragraphs = text.split("\n\n")
    return [p.strip() for p in paragraphs if p.strip()]


def split_large_text(
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


def get_overlap_parts(
    parts: list[str],
    chunk_overlap: int,
    encoding: TextEncoding,
) -> list[str]:
    """Get parts from the end that fit within the overlap size."""
    overlap_parts: list[str] = []
    overlap_tokens = 0

    for part in reversed(parts):
        part_tokens = count_tokens(part, encoding)
        if overlap_tokens + part_tokens <= chunk_overlap:
            overlap_parts.insert(0, part)
            overlap_tokens += part_tokens
        else:
            break
    return overlap_parts


def split_large_text_by_blocks(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    encoding: TextEncoding,
) -> list[str]:
    """Split large text on paragraph boundaries before falling back to tokens."""
    blocks = split_text(text)
    if len(blocks) <= 1:
        return split_large_text(text, chunk_size, chunk_overlap, encoding)

    sub_chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    for block in blocks:
        block_tokens = count_tokens(block, encoding)

        if block_tokens > chunk_size:
            if current_parts:
                sub_chunks.append("\n\n".join(current_parts).strip())
                current_parts = []
                current_tokens = 0

            # Legal clauses and list items are atomic retrieval units. Preserve the boundary.
            sub_chunks.append(block)
            continue

        if current_parts and current_tokens + block_tokens > chunk_size:
            sub_chunks.append("\n\n".join(current_parts).strip())
            current_parts = get_overlap_parts(current_parts, chunk_overlap, encoding)
            current_tokens = sum(count_tokens(part, encoding) for part in current_parts)

        current_parts.append(block)
        current_tokens += block_tokens

    if current_parts:
        sub_chunks.append("\n\n".join(current_parts).strip())

    return [chunk for chunk in sub_chunks if chunk]


def chunk_recursive(
    text: str,
    document_id: str,
    chunk_size: int,
    chunk_overlap: int,
    encoding: TextEncoding,
    page_number: int | None = None,
) -> list[Chunk]:
    """Chunk document text by paragraphs and token sizes with overlap."""
    paragraphs = split_text(text)
    chunks: list[Chunk] = []
    current_parts: list[str] = []
    current_tokens = 0

    base_metadata = {"document_id": document_id}
    if page_number is not None:
        base_metadata["page_number"] = page_number

    for paragraph in paragraphs:
        para_tokens = count_tokens(paragraph, encoding)

        if para_tokens > chunk_size:
            if current_parts:
                chunk_text = "\n\n".join(current_parts)
                chunks.append(
                    Chunk(
                        index=len(chunks),
                        content=chunk_text,
                        token_count=count_tokens(chunk_text, encoding),
                        metadata=base_metadata.copy(),
                    )
                )
                current_parts = []
                current_tokens = 0

            sub_chunks = split_large_text(paragraph, chunk_size, chunk_overlap, encoding)
            for sub in sub_chunks:
                chunks.append(
                    Chunk(
                        index=len(chunks),
                        content=sub,
                        token_count=count_tokens(sub, encoding),
                        metadata=base_metadata.copy(),
                    )
                )
            continue

        if current_tokens + para_tokens > chunk_size and current_parts:
            chunk_text = "\n\n".join(current_parts)
            chunks.append(
                Chunk(
                    index=len(chunks),
                    content=chunk_text,
                    token_count=count_tokens(chunk_text, encoding),
                    metadata=base_metadata.copy(),
                )
            )

            overlap_parts = get_overlap_parts(current_parts, chunk_overlap, encoding)
            current_parts = overlap_parts
            current_tokens = sum(count_tokens(p, encoding) for p in current_parts)

        current_parts.append(paragraph)
        current_tokens += para_tokens

    if current_parts:
        chunk_text = "\n\n".join(current_parts)
        chunks.append(
            Chunk(
                index=len(chunks),
                content=chunk_text,
                token_count=count_tokens(chunk_text, encoding),
                metadata=base_metadata.copy(),
            )
        )

    return chunks


__all__ = [
    "split_text",
    "split_large_text",
    "split_large_text_by_blocks",
    "get_overlap_parts",
    "chunk_recursive",
]
