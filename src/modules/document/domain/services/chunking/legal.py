"""Legal structure-aware document chunking strategy.

Preserves Vietnamese legal headings (Chương, Điều, Phụ lục) as atomic units
and prevents breaking legal clauses across inappropriate token boundaries.
"""

from src.modules.document.domain.constants import CHUNKER_PAGE_MARKER_PATTERN, LEGAL_HEADING_PATTERN
from src.modules.document.domain.models import Chunk
from src.modules.document.domain.services.chunking.recursive import split_large_text_by_blocks
from src.modules.document.domain.services.token_counter import (
    TextEncoding,
    count_tokens,
)


def get_page_range(text: str) -> tuple[int | None, int | None]:
    """Extract minimum and maximum page markers present in text."""
    pages = [int(match.group(1)) for match in CHUNKER_PAGE_MARKER_PATTERN.finditer(text)]
    if not pages:
        return None, None
    return min(pages), max(pages)


def get_active_page_marker_before(text: str, offset: int) -> str | None:
    """Find the most recent page marker before the given character offset."""
    marker = None
    for match in CHUNKER_PAGE_MARKER_PATTERN.finditer(text, 0, offset):
        marker = match.group(0)
    return marker


def extract_section_label(text: str) -> tuple[str, str]:
    """Extract section type (article, chapter, appendix) and title."""
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


def split_legal_sections(text: str) -> list[str]:
    """Split text into legal sections based on Chương / Điều / Phụ lục headings."""
    matches = list(LEGAL_HEADING_PATTERN.finditer(text))
    if not matches:
        return []

    sections: list[str] = []
    if matches[0].start() > 0:
        intro = text[: matches[0].start()].strip()
        if intro:
            sections.append(intro)

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[start:end].strip()
        if section:
            active_marker = get_active_page_marker_before(text, start)
            if active_marker and not CHUNKER_PAGE_MARKER_PATTERN.search(section):
                section = f"{active_marker}\n{section}"
            elif active_marker and not section.startswith(active_marker):
                first_marker = CHUNKER_PAGE_MARKER_PATTERN.search(section)
                if first_marker and first_marker.start() > 0:
                    section = f"{active_marker}\n{section}"
            sections.append(section)

    return sections


def chunk_legal_document(
    text: str,
    document_id: str,
    chunk_size: int,
    chunk_overlap: int,
    encoding: TextEncoding,
) -> list[Chunk]:
    """Chunk document respecting legal structure boundaries."""
    sections = split_legal_sections(text)
    chunks: list[Chunk] = []

    for section in sections:
        section_type, label = extract_section_label(section)
        page_start, page_end = get_page_range(section)
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

        token_count = count_tokens(section, encoding)
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

        sub_chunks = split_large_text_by_blocks(section, chunk_size, chunk_overlap, encoding)
        for sub_index, sub in enumerate(sub_chunks):
            sub_metadata = metadata.copy()
            sub_metadata["section_part"] = sub_index + 1
            sub_page_start, sub_page_end = get_page_range(sub)
            if sub_page_start is not None:
                sub_metadata["page_start"] = sub_page_start
                sub_metadata["page_end"] = sub_page_end
            chunks.append(
                Chunk(
                    index=len(chunks),
                    content=sub,
                    token_count=count_tokens(sub, encoding),
                    metadata=sub_metadata,
                )
            )

    return chunks


__all__ = [
    "split_legal_sections",
    "chunk_legal_document",
    "extract_section_label",
    "get_page_range",
    "get_active_page_marker_before",
]
