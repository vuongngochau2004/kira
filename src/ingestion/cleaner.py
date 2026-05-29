"""Text cleaning and preprocessing for document ingestion."""

import re
import unicodedata


def _strip_html(text: str) -> str:
    """Remove HTML tags from text, preserving content."""
    clean = re.sub(r"<[^>]+>", " ", text)
    return clean


def _normalize(text: str) -> str:
    """Normalize text: NFC unicode normalization + whitespace cleanup."""
    # Unicode normalization
    text = unicodedata.normalize("NFC", text)
    # Normalize whitespace: multiple spaces/tabs/newlines -> single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_document(text: str) -> str:
    """Clean document text.

    Args:
        text: Raw document text

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    raw = text
    if "<" in raw and ">" in raw:
        raw = _strip_html(raw)

    cleaned = _normalize(raw)
    return cleaned


def clean_chunks(chunks: list[dict]) -> list[dict]:
    """Clean multiple chunks.

    Args:
        chunks: List of chunk dicts with content/text

    Returns:
        List of cleaned chunks
    """
    cleaned = []
    for chunk in chunks:
        content = chunk.get("content", chunk.get("text", ""))
        cleaned_chunk = chunk.copy()
        cleaned_chunk["content"] = clean_document(content)
        if "text" in cleaned_chunk:
            cleaned_chunk["text"] = cleaned_chunk["content"]
        cleaned.append(cleaned_chunk)
    return cleaned


__all__ = ["clean_document", "clean_chunks", "_normalize", "_strip_html"]
