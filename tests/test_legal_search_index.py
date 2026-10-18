from datetime import date

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from src.modules.legal.application.records import LegalDocumentMetadata
from src.modules.legal.domain.models import BaseProvisionText, ProvisionChange, RelationType
from src.modules.legal.domain.timeline import build_timeline
from src.modules.legal.infrastructure.search_index import (
    OPEN_ENDED_VALID_TO,
    QdrantLegalSearchIndex,
)
from src.shared.ports.embedding import EmbeddingPort

COLLECTION = "legal_provisions_test"
KEY = "31/2024/QH15#D3.K1"
META = LegalDocumentMetadata(
    number="31/2024/QH15",
    doc_type="law",
    title="Luật Đất đai",
    issuer="Quốc hội",
    issued_date=date(2024, 1, 18),
    effective_date=date(2024, 8, 1),
)


class FakeEmbedding(EmbeddingPort):
    async def embed(self, text: str) -> list[float]:
        return [float(len(text) % 7) + 1.0, 1.0, 0.5, 0.25]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(text) for text in texts]

    @property
    def dimension(self) -> int:
        return 4

    async def health_check(self) -> bool:
        return True


def _versions(*amendment_dates: date):
    changes = [
        ProvisionChange(f"c{i}", RelationType.AMENDS, day, f"Nội dung {i}", "99/2026/QH15#D1.K1")
        for i, day in enumerate(amendment_dates)
    ]
    return build_timeline(KEY, BaseProvisionText(KEY, "Nội dung gốc", date(2024, 8, 1), 2), changes)


def _points(client: QdrantClient, key: str = KEY):
    points, _ = client.scroll(
        COLLECTION,
        scroll_filter=Filter(
            must=[FieldCondition(key="provision_key", match=MatchValue(value=key))]
        ),
        with_payload=True,
        limit=100,
    )
    return sorted(points, key=lambda point: point.payload["valid_from_ord"])


@pytest.fixture
def index() -> tuple[QdrantLegalSearchIndex, QdrantClient]:
    client = QdrantClient(":memory:")
    return QdrantLegalSearchIndex(client, FakeEmbedding(), COLLECTION), client


async def test_ensure_collection_is_idempotent(index) -> None:
    search_index, client = index
    await search_index.ensure_collection()
    await search_index.ensure_collection()
    assert client.collection_exists(COLLECTION)


async def test_versions_are_indexed_with_validity_payload(index) -> None:
    search_index, client = index
    await search_index.ensure_collection()
    versions = _versions(date(2026, 7, 1))
    await search_index.replace_provision_versions(KEY, META, "Khoản 1", versions)

    points = _points(client)
    assert [str(p.id) for p in points] == [str(v.version_id) for v in versions]
    first, second = (p.payload for p in points)
    assert first["valid_from"] == "2024-08-01"
    assert first["valid_to"] == "2026-07-01"
    assert first["valid_to_ord"] == date(2026, 7, 1).toordinal()
    assert first["number"] == "31/2024/QH15"
    assert first["label"] == "Khoản 1"
    assert first["page"] == 2
    assert second["valid_to"] is None
    assert second["valid_to_ord"] == OPEN_ENDED_VALID_TO.toordinal()
    assert second["text"] == "Nội dung 0"


async def test_replacing_removes_stale_versions_only_for_that_provision(index) -> None:
    search_index, client = index
    await search_index.ensure_collection()
    other_key = "31/2024/QH15#D4"
    other = build_timeline(other_key, BaseProvisionText(other_key, "Điều 4", date(2024, 8, 1)), [])
    await search_index.replace_provision_versions(other_key, META, "Điều 4", other)
    await search_index.replace_provision_versions(KEY, META, "Khoản 1", _versions(date(2026, 7, 1)))

    await search_index.replace_provision_versions(KEY, META, "Khoản 1", _versions())

    assert len(_points(client)) == 1
    assert _points(client)[0].payload["valid_to"] is None
    assert len(_points(client, other_key)) == 1


async def test_empty_version_list_deletes_all_points_of_provision(index) -> None:
    search_index, client = index
    await search_index.ensure_collection()
    await search_index.replace_provision_versions(KEY, META, "Khoản 1", _versions())
    await search_index.replace_provision_versions(KEY, META, "Khoản 1", [])
    assert _points(client) == []


async def test_point_ids_are_version_ids(index) -> None:
    search_index, client = index
    await search_index.ensure_collection()
    versions = _versions()
    await search_index.replace_provision_versions(KEY, META, "Khoản 1", versions)
    await search_index.replace_provision_versions(KEY, META, "Khoản 1", versions)
    assert [str(p.id) for p in _points(client)] == [str(versions[0].version_id)]
