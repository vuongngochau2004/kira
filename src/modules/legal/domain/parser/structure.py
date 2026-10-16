"""Parse Vietnamese legal text into an Article → Clause → Point tree."""

import re
from dataclasses import dataclass, field

from src.modules.legal.domain.errors import LegalParseError
from src.modules.legal.domain.models import ParsedProvision, ParseResult, ProvisionLevel
from src.modules.legal.domain.provision_key import build_provision_key

UNBALANCED_QUOTES_WARNING = "unbalanced_quotes"
DUPLICATE_PROVISION_KEY_WARNING = "duplicate_provision_key"

_PREFIX = r"^\s*(?:#{1,6}\s*)?(?:\*\*)?\s*"
_SUFFIX = r"\s*(?:\*\*)?\s*$"
_PAGE_MARKER = re.compile(r"^\s*<!--\s*page\s+(\d+)\s*-->\s*$", re.IGNORECASE)
_CHAPTER = re.compile(
    _PREFIX + r"Chương\s+([IVXLCDM]+|\d+)\b\s*[.:-]?\s*(.*?)" + _SUFFIX, re.IGNORECASE
)
_ARTICLE = re.compile(_PREFIX + r"Điều\s+(\d+[a-zđ]?)\s*[.:]\s*(.*?)" + _SUFFIX, re.IGNORECASE)
_APPENDIX = re.compile(_PREFIX + r"Phụ\s*lục\b", re.IGNORECASE)
_CLAUSE = re.compile(r"^\s*(\d+)\s*\.\s+\S")
_POINT = re.compile(r"^\s*([a-zđ])\s*\)\s+\S")
_LEADING_NUMBER = re.compile(r"\d+")


@dataclass
class _Builder:
    key: str
    level: ProvisionLevel
    label: str
    heading: str
    chapter_label: str | None
    page: int | None
    parent_key: str | None
    lines: list[str] = field(default_factory=list)

    def build(self) -> ParsedProvision:
        return ParsedProvision(
            provision_key=self.key,
            level=self.level,
            label=self.label,
            heading=self.heading,
            chapter_label=self.chapter_label,
            text="\n".join(self.lines).strip(),
            page=self.page,
            parent_key=self.parent_key,
        )


class _QuoteTracker:
    """Track whether the parser is inside quoted (amended) content."""

    def __init__(self) -> None:
        self._curly_depth = 0
        self._straight_open = False

    @property
    def inside(self) -> bool:
        return self._curly_depth > 0 or self._straight_open

    @property
    def balanced(self) -> bool:
        return self._curly_depth == 0 and not self._straight_open

    def feed(self, line: str) -> None:
        self._curly_depth = max(0, self._curly_depth + line.count("“") - line.count("”"))
        if line.count('"') % 2 == 1:
            self._straight_open = not self._straight_open

    def reset(self) -> None:
        self._curly_depth = 0
        self._straight_open = False


def parse_legal_structure(text: str, number: str) -> ParseResult:
    """Parse legal text into provisions keyed by `number`.

    An unclosed quotation mark is assumed to end at the next top-level article of
    this document (the article number following the current one).
    """
    preamble, provisions, warnings = _parse(text, number)
    if not any(p.level is ProvisionLevel.ARTICLE for p in provisions):
        raise LegalParseError(f"No articles found in legal document {number}")
    return ParseResult(preamble=preamble, provisions=tuple(provisions), warnings=tuple(warnings))


def _parse(text: str, number: str) -> tuple[str, list[ParsedProvision], list[str]]:
    quotes = _QuoteTracker()
    warnings: list[str] = []
    builders: dict[str, _Builder] = {}
    preamble: list[str] = []
    page: int | None = None
    chapter: str | None = None
    awaiting_chapter_title = False
    in_appendix = False
    article: _Builder | None = None
    clause: _Builder | None = None
    point: _Builder | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        page_match = _PAGE_MARKER.match(line)
        if page_match:
            page = int(page_match.group(1))
            continue
        if in_appendix:
            continue

        structural = not quotes.inside
        if not structural and article is not None and _closes_broken_quote(line, article):
            quotes.reset()
            _warn(warnings, UNBALANCED_QUOTES_WARNING)
            structural = True
        quotes.feed(line)

        if structural:
            if _APPENDIX.match(line):
                in_appendix = True
                continue

            chapter_match = _CHAPTER.match(line)
            if chapter_match:
                chapter = f"Chương {chapter_match.group(1).upper()}"
                title = chapter_match.group(2).strip()
                if title:
                    chapter = f"{chapter}. {title}"
                awaiting_chapter_title = not title
                continue

            article_match = _ARTICLE.match(line)
            if article_match:
                article_id = article_match.group(1).lower()
                key = build_provision_key(number, article_id)
                if key not in builders:
                    heading = article_match.group(2).strip()
                    label = f"Điều {article_id}"
                    article = _Builder(
                        key, ProvisionLevel.ARTICLE, label, heading, chapter, page, None
                    )
                    article.lines.append(f"{label}. {heading}" if heading else label)
                    builders[key] = article
                    clause = None
                    point = None
                    awaiting_chapter_title = False
                    continue
                _warn(warnings, DUPLICATE_PROVISION_KEY_WARNING)

            if awaiting_chapter_title:
                chapter = f"{chapter}. {line}"
                awaiting_chapter_title = False
                continue

            if article is not None:
                clause_match = _CLAUSE.match(line)
                if clause_match:
                    clause_number = clause_match.group(1)
                    key = f"{article.key}.K{clause_number}"
                    if key not in builders:
                        clause = _Builder(
                            key,
                            ProvisionLevel.CLAUSE,
                            f"Khoản {clause_number}",
                            "",
                            article.chapter_label,
                            page,
                            article.key,
                            [line],
                        )
                        builders[key] = clause
                        point = None
                        continue
                    _warn(warnings, DUPLICATE_PROVISION_KEY_WARNING)

            if clause is not None:
                point_match = _POINT.match(line)
                if point_match:
                    letter = point_match.group(1).lower()
                    key = f"{clause.key}.{letter}"
                    if key not in builders:
                        point = _Builder(
                            key,
                            ProvisionLevel.POINT,
                            f"Điểm {letter}",
                            "",
                            clause.chapter_label,
                            page,
                            clause.key,
                            [line],
                        )
                        builders[key] = point
                        continue
                    _warn(warnings, DUPLICATE_PROVISION_KEY_WARNING)

        target = point or clause or article
        if target is None:
            preamble.append(line)
        else:
            target.lines.append(line)

    if not quotes.balanced:
        _warn(warnings, UNBALANCED_QUOTES_WARNING)
    provisions = [builder.build() for builder in builders.values()]
    return "\n".join(preamble), provisions, warnings


def _closes_broken_quote(line: str, article: _Builder) -> bool:
    """An unquoted heading of the next article means the open quote was never closed."""
    match = _ARTICLE.match(line)
    if match is None:
        return False
    return _article_number(match.group(1)) == _article_number(article.label) + 1


def _article_number(article_id: str) -> int:
    match = _LEADING_NUMBER.search(article_id)
    return int(match.group()) if match else -1


def _warn(warnings: list[str], warning: str) -> None:
    if warning not in warnings:
        warnings.append(warning)
