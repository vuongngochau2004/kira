from datetime import date
from uuid import uuid4

import pytest

from src.modules.legal.domain.errors import TimelineConflict
from src.modules.legal.domain.models import ProvisionVersion
from src.modules.legal.domain.provision_key import (
    build_provision_key,
    build_provision_ref,
    iter_vietnamese_ref_groups,
    iter_vietnamese_refs,
    parse_vietnamese_ref,
)


def test_build_provision_key_levels() -> None:
    assert build_provision_key("31/2024/QH15", "12") == "31/2024/QH15#D12"
    assert build_provision_key("31/2024/QH15", "12", "3") == "31/2024/QH15#D12.K3"
    assert build_provision_key("31/2024/QH15", "12", "3", "a") == "31/2024/QH15#D12.K3.a"


def test_point_requires_clause() -> None:
    with pytest.raises(ValueError):
        build_provision_ref("12", None, "a")


def test_parse_vietnamese_ref_variants() -> None:
    assert parse_vietnamese_ref("điểm a khoản 3 Điều 12") == "D12.K3.a"
    assert parse_vietnamese_ref("khoản 2 Điều 5 của Luật") == "D5.K2"
    assert parse_vietnamese_ref("Bổ sung Điều 12a vào sau Điều 12") == "D12a"
    assert parse_vietnamese_ref("không có tham chiếu") is None


def test_iter_vietnamese_refs_finds_all_refs() -> None:
    assert list(iter_vietnamese_refs("khoản 3 Điều 5 và Điều 7 của Nghị định")) == ["D5.K3", "D7"]


def test_provision_version_in_force_boundaries() -> None:
    version = ProvisionVersion(
        version_id=uuid4(),
        provision_key="31/2024/QH15#D1",
        text="x",
        text_hash="h",
        valid_from=date(2024, 8, 1),
        valid_to=date(2026, 7, 1),
        page=None,
        introduced_by=None,
    )
    assert not version.in_force_on(date(2024, 7, 31))
    assert version.in_force_on(date(2024, 8, 1))
    assert version.in_force_on(date(2026, 6, 30))
    assert not version.in_force_on(date(2026, 7, 1))


def test_open_ended_version_in_force_forever() -> None:
    version = ProvisionVersion(uuid4(), "k", "x", "h", date(2024, 8, 1), None, None, None)
    assert version.in_force_on(date(2999, 1, 1))


def test_timeline_conflict_carries_ids() -> None:
    error = TimelineConflict(["b", "a"], "same_effective_date")
    assert error.change_ids == ("b", "a")
    assert error.reason == "same_effective_date"


def test_ref_lists_expand_to_each_item() -> None:
    assert list(iter_vietnamese_refs("Bãi bỏ các điểm a và b khoản 2 Điều 5")) == [
        "D5.K2.a",
        "D5.K2.b",
    ]
    assert list(iter_vietnamese_refs("khoản 1, khoản 2 Điều 3")) == ["D3.K1", "D3.K2"]


def test_ref_groups_keep_list_boundaries() -> None:
    assert list(iter_vietnamese_ref_groups("khoản 2 và khoản 3 Điều 5; Điều 7")) == [
        ["D5.K2", "D5.K3"],
        ["D7"],
    ]


def test_inserted_clause_ids_are_parsed() -> None:
    assert parse_vietnamese_ref("khoản 3a Điều 10") == "D10.K3a"
