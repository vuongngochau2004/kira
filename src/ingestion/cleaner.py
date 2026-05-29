"""Text cleaning and preprocessing for document ingestion."""

import re
import unicodedata


def _strip_html(text: str) -> str:
    """Remove HTML tags from text, preserving content."""
    clean = re.sub(r"<[^>]+>", " ", text)
    return clean


def _normalize(text: str) -> str:
    """Normalize text: NFC unicode normalization + within-paragraph whitespace cleanup."""
    # Unicode normalization
    text = unicodedata.normalize("NFC", text)
    # Clean spaces/tabs ONLY within paragraphs - preserve newlines
    text = re.sub(r"[ \t]+", " ", text)
    # Remove trailing spaces from each line
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def clean_document(text: str) -> str:
    """Clean document text while preserving paragraph structure.

    Args:
        text: Raw document text

    Returns:
        Cleaned text with preserved paragraph boundaries (\n\n)
    """
    if not text:
        return ""

    raw = text
    if "<" in raw and ">" in raw:
        raw = _strip_html(raw)

    # Split into paragraphs first to preserve structure
    paragraphs = raw.split("\n\n")
    cleaned_paragraphs = []

    for para in paragraphs:
        # Normalize within paragraph only
        cleaned = _normalize(para)
        if cleaned.strip():
            cleaned_paragraphs.append(cleaned)

    # Rejoin with double newlines to preserve paragraph structure
    return "\n\n".join(cleaned_paragraphs)


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
