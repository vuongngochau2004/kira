"""Domain types for answering legal questions."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date
from typing import Literal

SourceRole = Literal["primary", "guide", "before", "after", "removed", "added"]


@dataclass(frozen=True)
class ProvisionHit:
    """One provision version returned by a search, with its validity interval."""

    version_id: str
    provision_key: str
    number: str
    doc_type: str
    title: str
    label: str
    text: str
    page: int | None
    valid_from: date
    valid_to: date | None
    score: float = 0.0

    def in_force_on(self, day: date) -> bool:
        return self.valid_from <= day and (self.valid_to is None or day < self.valid_to)


@dataclass(frozen=True)
class LegalSource:
    """A provision version placed in the answer context, with graph-derived notes."""

    hit: ProvisionHit
    role: SourceRole = "primary"
    parent_label: str | None = None
    parent_text: str | None = None
    amended_after: date | None = None
    introduced_by_number: str | None = None
    introduced_by_title: str | None = None


def fuse_hits(rankings: Sequence[Sequence[ProvisionHit]], k: int = 60) -> list[ProvisionHit]:
    """Reciprocal rank fusion keyed by version id; the fused score replaces `score`."""
    scores: dict[str, float] = {}
    first_seen: dict[str, ProvisionHit] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking):
            scores[hit.version_id] = scores.get(hit.version_id, 0.0) + 1.0 / (k + rank + 1)
            first_seen.setdefault(hit.version_id, hit)
    ordered = sorted(scores, key=lambda version_id: scores[version_id], reverse=True)
    return [replace(first_seen[version_id], score=scores[version_id]) for version_id in ordered]
