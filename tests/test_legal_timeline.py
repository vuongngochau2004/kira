import random
from datetime import date, timedelta

import pytest

from src.modules.legal.domain.errors import TimelineConflict
from src.modules.legal.domain.models import BaseProvisionText, ProvisionChange, RelationType
from src.modules.legal.domain.timeline import build_timeline, version_in_force

KEY = "31/2024/QH15#D3.K1"
BASE = BaseProvisionText(KEY, "v0", date(2024, 8, 1), page=4)


def _amend(change_id: str, day: date, text: str) -> ProvisionChange:
    return ProvisionChange(
        change_id=change_id,
        type=RelationType.AMENDS,
        effective_date=day,
        new_text=text,
        source_provision_key=f"99/2026/QH15#D1.{change_id}",
    )


def test_base_only_gives_one_open_version_with_stable_id() -> None:
    first = build_timeline(KEY, BASE, [])
    second = build_timeline(KEY, BASE, [])
    assert len(first) == 1
    assert first[0].valid_from == date(2024, 8, 1)
    assert first[0].valid_to is None
    assert first[0].page == 4
    assert first[0].introduced_by is None
    assert first[0].version_id == second[0].version_id


def test_out_of_order_amendments_build_sorted_chain() -> None:
    versions = build_timeline(
        KEY,
        BASE,
        [_amend("K2", date(2026, 7, 1), "v2"), _amend("K1", date(2025, 1, 1), "v1")],
    )
    assert [v.text for v in versions] == ["v0", "v1", "v2"]
    assert [(v.valid_from, v.valid_to) for v in versions] == [
        (date(2024, 8, 1), date(2025, 1, 1)),
        (date(2025, 1, 1), date(2026, 7, 1)),
        (date(2026, 7, 1), None),
    ]
    assert versions[1].introduced_by == "99/2026/QH15#D1.K1"


def test_repeal_closes_timeline() -> None:
    repeal = ProvisionChange("r", RelationType.REPEALS, date(2026, 7, 1))
    versions = build_timeline(KEY, BASE, [repeal])
    assert len(versions) == 1
    assert versions[0].valid_to == date(2026, 7, 1)
    assert version_in_force(versions, date(2026, 7, 1)) is None


def test_change_after_repeal_conflicts() -> None:
    repeal = ProvisionChange("r", RelationType.REPEALS, date(2026, 7, 1))
    with pytest.raises(TimelineConflict) as error:
        build_timeline(KEY, BASE, [repeal, _amend("late", date(2027, 1, 1), "v9")])
    assert error.value.change_ids == ("late",)
    assert error.value.reason == "change_after_termination"


def test_same_effective_date_conflicts() -> None:
    with pytest.raises(TimelineConflict) as error:
        build_timeline(
            KEY, BASE, [_amend("b", date(2026, 7, 1), "x"), _amend("a", date(2026, 7, 1), "y")]
        )
    assert error.value.change_ids == ("a", "b")
    assert error.value.reason == "same_effective_date"


def test_change_before_base_conflicts() -> None:
    with pytest.raises(TimelineConflict) as error:
        build_timeline(KEY, BASE, [_amend("early", date(2020, 1, 1), "x")])
    assert error.value.reason == "before_base"


def test_amendment_on_base_day_drops_zero_length_version() -> None:
    versions = build_timeline(KEY, BASE, [_amend("same", date(2024, 8, 1), "v1")])
    assert [v.text for v in versions] == ["v1"]
    assert version_in_force(versions, date(2024, 8, 1)).text == "v1"  # type: ignore[union-attr]


def test_inserted_provision_starts_at_amendment() -> None:
    versions = build_timeline(KEY, None, [_amend("ins", date(2026, 7, 1), "Điều 3a. Mới")])
    assert len(versions) == 1
    assert versions[0].valid_from == date(2026, 7, 1)


def test_inserted_provision_cannot_start_with_repeal() -> None:
    repeal = ProvisionChange("r", RelationType.REPEALS, date(2026, 7, 1))
    with pytest.raises(TimelineConflict) as error:
        build_timeline(KEY, None, [repeal])
    assert error.value.reason == "terminates_missing_provision"


def test_rejects_non_timeline_types_and_empty_amendments() -> None:
    with pytest.raises(ValueError):
        build_timeline(KEY, BASE, [ProvisionChange("g", RelationType.GUIDES, date(2026, 1, 1))])
    with pytest.raises(ValueError):
        build_timeline(
            KEY, BASE, [ProvisionChange("e", RelationType.AMENDS, date(2026, 1, 1), " ")]
        )


def test_rejects_mismatched_base_key() -> None:
    with pytest.raises(ValueError):
        build_timeline("other#D1", BASE, [])


def test_random_timelines_never_overlap() -> None:
    rng = random.Random(20260701)
    start = date(2024, 8, 1)
    for _ in range(200):
        offsets = rng.sample(range(1, 2000), k=rng.randint(0, 6))
        changes = [
            _amend(f"c{i}", start + timedelta(days=offset), f"text {i}")
            for i, offset in enumerate(offsets)
        ]
        if offsets and rng.random() < 0.3:
            end = start + timedelta(days=max(offsets) + rng.randint(1, 100))
            changes.append(ProvisionChange("repeal", RelationType.REPEALS, end))
        versions = build_timeline(KEY, BaseProvisionText(KEY, "base", start), changes)
        assert len({v.version_id for v in versions}) == len(versions)
        for earlier, later in zip(versions, versions[1:], strict=False):
            assert earlier.valid_to == later.valid_from
        for offset in range(0, 2200, 7):
            day = start + timedelta(days=offset)
            assert sum(v.in_force_on(day) for v in versions) <= 1
