from datetime import date

import pytest
from qdrant_client import QdrantClient

from src.modules.legal.application.records import LegalDocumentMetadata
from src.modules.legal.domain.models import BaseProvisionText, ProvisionChange, RelationType
from src.modules.legal.domain.qa import fuse_hits
from src.modules.legal.domain.timeline import build_timeline
from src.modules.legal.infrastructure.search_index import QdrantLegalSearchIndex
from tests.legal_fakes import make_hit
from tests.test_legal_search_index import FakeEmbedding

COLLECTION = "legal_qa_test"
LAW = LegalDocumentMetadata(
    "31/2024/QH15", "law", "Luật Đất đai", "Quốc hội", date(2024, 1, 18), date(2024, 8, 1)
)
DECREE = LegalDocumentMetadata(
    "10/2026/NĐ-CP",
    "decree",
    "Nghị định hướng dẫn",
    "Chính phủ",
    date(2026, 6, 1),
    date(2026, 7, 1),
)


@pytest.fixture
async def index() -> QdrantLegalSearchIndex:
    search_index = QdrantLegalSearchIndex(QdrantClient(":memory:"), FakeEmbedding(), COLLECTION)
    await search_index.ensure_collection()
    key = "31/2024/QH15#D3.K1"
    amended = build_timeline(
        key,
        BaseProvisionText(key, "1. Quy hoạch cũ.", date(2024, 8, 1)),
        [ProvisionChange("c1", RelationType.AMENDS, date(2026, 7, 1), "1. Quy hoạch mới.")],
    )
    await search_index.replace_provision_versions(key, LAW, "Khoản 1", amended)
    decree_key = "10/2026/NĐ-CP#D5"
    decree = build_timeline(
        decree_key, BaseProvisionText(decree_key, "Điều 5. Trình tự.", date(2026, 7, 1)), []
    )
    await search_index.replace_provision_versions(decree_key, DECREE, "Điều 5", decree)
    return search_index


async def test_search_returns_only_versions_in_force(index) -> None:
    vector = [1.0, 1.0, 0.5, 0.25]
    before = await index.search_in_force(vector, date(2025, 1, 1), 10)
    assert [(h.provision_key, h.text) for h in before] == [
        ("31/2024/QH15#D3.K1", "1. Quy hoạch cũ.")
    ]
    after = await index.search_in_force(vector, date(2026, 7, 1), 10)
    assert {h.text for h in after} == {"1. Quy hoạch mới.", "Điều 5. Trình tự."}
    hit = next(h for h in after if h.number == "31/2024/QH15")
    assert (hit.label, hit.title, hit.valid_from, hit.valid_to) == (
        "Khoản 1",
        "Luật Đất đai",
        date(2026, 7, 1),
        None,
    )
    assert hit.score > 0


async def test_search_filters_by_keys_and_numbers(index) -> None:
    vector = [1.0, 1.0, 0.5, 0.25]
    by_number = await index.search_in_force(vector, date(2026, 8, 1), 10, numbers=["10/2026/NĐ-CP"])
    assert [h.provision_key for h in by_number] == ["10/2026/NĐ-CP#D5"]
    by_key = await index.search_in_force(
        vector, date(2026, 8, 1), 10, provision_keys=["31/2024/QH15#D3.K1"]
    )
    assert [h.provision_key for h in by_key] == ["31/2024/QH15#D3.K1"]
    assert await index.search_in_force(vector, date(2026, 8, 1), 10, provision_keys=[]) == []


async def test_list_and_count_versions(index) -> None:
    assert await index.count_versions() == 3
    history = await index.list_versions("31/2024/QH15#D3.K1")
    assert sorted(h.valid_from for h in history) == [date(2024, 8, 1), date(2026, 7, 1)]
    assert len(await index.list_versions()) == 3


async def test_missing_collection_is_empty() -> None:
    empty = QdrantLegalSearchIndex(QdrantClient(":memory:"), FakeEmbedding(), "absent")
    assert await empty.search_in_force([1.0, 0, 0, 0], date(2026, 1, 1), 5) == []
    assert await empty.count_versions() == 0
    assert await empty.list_versions() == []


def test_fuse_hits_rewards_agreement() -> None:
    a = make_hit("31/2024/QH15#D1", "a", date(2024, 8, 1))
    b = make_hit("31/2024/QH15#D2", "b", date(2024, 8, 1))
    c = make_hit("31/2024/QH15#D3", "c", date(2024, 8, 1))
    fused = fuse_hits([[a, b], [b, c]])
    assert [h.provision_key for h in fused] == [
        "31/2024/QH15#D2",
        "31/2024/QH15#D1",
        "31/2024/QH15#D3",
    ]
    assert fused[0].score > fused[1].score
