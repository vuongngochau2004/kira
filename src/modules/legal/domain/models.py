"""Domain models for the Vietnamese legal knowledge graph."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID


class ProvisionLevel(StrEnum):
    ARTICLE = "article"
    CLAUSE = "clause"
    POINT = "point"


class RelationType(StrEnum):
    AMENDS = "AMENDS"
    REPEALS = "REPEALS"
    REPLACES = "REPLACES"
    GUIDES = "GUIDES"
    BASED_ON = "BASED_ON"


TIMELINE_RELATION_TYPES: frozenset[RelationType] = frozenset(
    {RelationType.AMENDS, RelationType.REPEALS, RelationType.REPLACES}
)


@dataclass(frozen=True)
class ParsedProvision:
    """One structural unit (Article, Clause, Point) with its own text only."""

    provision_key: str
    level: ProvisionLevel
    label: str
    heading: str
    chapter_label: str | None
    text: str
    page: int | None
    parent_key: str | None


@dataclass(frozen=True)
class ParseResult:
    preamble: str
    provisions: tuple[ParsedProvision, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class BaseProvisionText:
    """Original text of a provision as published in its own document."""

    provision_key: str
    text: str
    valid_from: date
    page: int | None = None


@dataclass(frozen=True)
class ProvisionChange:
    """An approved change that affects a provision's timeline."""

    change_id: str
    type: RelationType
    effective_date: date
    new_text: str | None = None
    source_provision_key: str | None = None
    page: int | None = None


@dataclass(frozen=True)
class ProvisionVersion:
    version_id: UUID
    provision_key: str
    text: str
    text_hash: str
    valid_from: date
    valid_to: date | None
    page: int | None
    introduced_by: str | None

    def in_force_on(self, day: date) -> bool:
        return self.valid_from <= day and (self.valid_to is None or day < self.valid_to)


@dataclass(frozen=True)
class RelationDraft:
    """A relation candidate proposed by an extractor, pending admin review."""

    type: RelationType
    target_number: str
    evidence_text: str
    confidence: float
    source_provision_key: str | None = None
    target_provision_ref: str | None = None
    new_text: str | None = None
    evidence_page: int | None = None
    extractor: str = "rule"
