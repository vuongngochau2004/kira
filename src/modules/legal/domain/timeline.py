"""Build non-overlapping provision version timelines from approved changes."""

import hashlib
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from itertools import groupby

from src.modules.legal.domain.errors import TimelineConflict
from src.modules.legal.domain.models import (
    TIMELINE_RELATION_TYPES,
    BaseProvisionText,
    ProvisionChange,
    ProvisionVersion,
    RelationType,
)

_VERSION_NAMESPACE = uuid.UUID("6f1c3a52-6a0e-4c43-9a43-1d6d0f0b9b11")


@dataclass(frozen=True)
class _Segment:
    text: str
    valid_from: date
    page: int | None
    introduced_by: str | None


def compute_text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def make_version_id(provision_key: str, valid_from: date, text_hash: str) -> uuid.UUID:
    return uuid.uuid5(_VERSION_NAMESPACE, f"{provision_key}|{valid_from.isoformat()}|{text_hash}")


def build_timeline(
    provision_key: str,
    base: BaseProvisionText | None,
    changes: Sequence[ProvisionChange],
) -> list[ProvisionVersion]:
    """Return the ordered, non-overlapping versions of one provision."""
    _validate(provision_key, base, changes)
    ordered = sorted(changes, key=lambda change: (change.effective_date, change.change_id))

    for _, group in groupby(ordered, key=lambda change: change.effective_date):
        same_day = [change.change_id for change in group]
        if len(same_day) > 1:
            raise TimelineConflict(same_day, "same_effective_date")

    if base is not None and ordered and ordered[0].effective_date < base.valid_from:
        raise TimelineConflict([ordered[0].change_id], "before_base")
    if base is None and ordered and ordered[0].type is not RelationType.AMENDS:
        raise TimelineConflict([ordered[0].change_id], "terminates_missing_provision")

    current: _Segment | None = (
        _Segment(base.text.strip(), base.valid_from, base.page, None) if base else None
    )
    terminated = False
    versions: list[ProvisionVersion] = []

    for change in ordered:
        if terminated:
            raise TimelineConflict([change.change_id], "change_after_termination")
        if current is not None:
            _emit(versions, provision_key, current, change.effective_date)
        if change.type is RelationType.AMENDS:
            assert change.new_text is not None
            current = _Segment(
                change.new_text.strip(),
                change.effective_date,
                change.page,
                change.source_provision_key,
            )
        else:
            current = None
            terminated = True

    if current is not None:
        _emit(versions, provision_key, current, None)
    return versions


def version_in_force(versions: Sequence[ProvisionVersion], day: date) -> ProvisionVersion | None:
    return next((version for version in versions if version.in_force_on(day)), None)


def _validate(
    provision_key: str, base: BaseProvisionText | None, changes: Sequence[ProvisionChange]
) -> None:
    if base is not None and base.provision_key != provision_key:
        raise ValueError(f"Base text belongs to {base.provision_key}, not {provision_key}")
    for change in changes:
        if change.type not in TIMELINE_RELATION_TYPES:
            raise ValueError(f"{change.type} does not change a provision timeline")
        if change.type is RelationType.AMENDS and not (change.new_text or "").strip():
            raise ValueError(f"Amendment {change.change_id} has no new text")


def _emit(
    versions: list[ProvisionVersion],
    provision_key: str,
    segment: _Segment,
    valid_to: date | None,
) -> None:
    if valid_to is not None and valid_to <= segment.valid_from:
        return
    text_hash = compute_text_hash(segment.text)
    versions.append(
        ProvisionVersion(
            version_id=make_version_id(provision_key, segment.valid_from, text_hash),
            provision_key=provision_key,
            text=segment.text,
            text_hash=text_hash,
            valid_from=segment.valid_from,
            valid_to=valid_to,
            page=segment.page,
            introduced_by=segment.introduced_by,
        )
    )
