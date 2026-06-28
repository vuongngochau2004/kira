"""Domain models and value objects for the document module."""

from dataclasses import dataclass, field

@dataclass
class ExtractionResult:
    """Result from text extraction."""
    text: str = ""
    pages: int = 0
    metadata: dict = field(default_factory=dict)
    success: bool = True
    error: str | None = None
    page_texts: list[tuple[int, str]] = field(default_factory=list)  # (page_num, text) for page tracking


@dataclass
class TextQualityReport:
    """Diagnostics for extracted text quality."""
    issues: list[str]
    score: int
    should_fallback: bool
    char_count: int
    word_count: int
    letter_count: int
    vi_diacritic_ratio: float
    unaccented_signal_ratio: float
    mojibake_count: int
    html_entity_count: int
    alphanumeric_artifact_ratio: float


@dataclass
class Chunk:
    """A chunk of text from a document."""
    index: int
    content: str
    token_count: int
    metadata: dict = field(default_factory=dict)

