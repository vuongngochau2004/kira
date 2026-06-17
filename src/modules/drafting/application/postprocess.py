"""Post-processing helpers for generated administrative drafts."""

import re


_DOCUMENT_CITATION_RE = re.compile(r"\s*\[Document\s+\d+\]", flags=re.IGNORECASE)
_TRAILING_SOURCES_RE = re.compile(
    r"\n+\s*(?:Tài liệu|Nguồn|Căn cứ)\s*/?\s*(?:căn cứ)?\s*đã sử dụng\s*:.*\Z",
    flags=re.IGNORECASE | re.DOTALL,
)


def clean_administrative_draft(content: str) -> str:
    """Remove retrieval artifacts and normalize a generated final draft."""
    cleaned = (content or "").replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _DOCUMENT_CITATION_RE.sub("", cleaned)
    cleaned = _TRAILING_SOURCES_RE.sub("", cleaned)

    normalized_lines: list[str] = []
    previous_blank = False
    for raw_line in cleaned.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        line = re.sub(r"\s+([,.;:])", r"\1", line)
        if not line:
            if normalized_lines and not previous_blank:
                normalized_lines.append("")
            previous_blank = True
            continue
        normalized_lines.append(line)
        previous_blank = False

    while normalized_lines and not normalized_lines[-1]:
        normalized_lines.pop()
    return "\n".join(normalized_lines)


__all__ = ["clean_administrative_draft"]
