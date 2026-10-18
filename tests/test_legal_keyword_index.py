from datetime import date

from src.modules.legal.infrastructure.keyword_index import LegalKeywordIndex
from tests.legal_fakes import FakeProvisionSearch, make_hit

OLD = make_hit(
    "31/2024/QH15#D3.K1",
    "Nhà nước quyết định quy hoạch sử dụng đất.",
    date(2024, 8, 1),
    date(2026, 7, 1),
)
NEW = make_hit(
    "31/2024/QH15#D3.K1", "Nhà nước quyết định quy hoạch và kế hoạch sử dụng đất.", date(2026, 7, 1)
)
FINE = make_hit(
    "100/2019/NĐ-CP#D5",
    "Phạt tiền người điều khiển xe vượt đèn đỏ.",
    date(2020, 1, 1),
    title="Nghị định xử phạt",
)


class CountingSource(FakeProvisionSearch):
    def __init__(self, hits) -> None:
        super().__init__(hits)
        self.list_calls = 0

    async def list_versions(self, provision_key=None):
        self.list_calls += 1
        return await super().list_versions(provision_key)


async def test_keyword_search_respects_validity() -> None:
    index = LegalKeywordIndex(CountingSource([OLD, NEW, FINE]), ttl_seconds=600)
    in_2025 = await index.search("quy hoạch sử dụng đất", date(2025, 1, 1), 5)
    assert [h.version_id for h in in_2025] == [OLD.version_id]
    in_2027 = await index.search("quy hoạch sử dụng đất", date(2027, 1, 1), 5)
    assert [h.version_id for h in in_2027] == [NEW.version_id]
    assert in_2027[0].score > 0


async def test_unrelated_query_returns_nothing() -> None:
    index = LegalKeywordIndex(CountingSource([OLD, NEW, FINE]), ttl_seconds=600)
    assert await index.search("thuế thu nhập cá nhân", date(2027, 1, 1), 5) == []


async def test_index_rebuilds_when_corpus_changes_or_ttl_expires() -> None:
    now = [0.0]
    source = CountingSource([OLD, FINE])
    index = LegalKeywordIndex(
        source, ttl_seconds=60, clock=lambda: now[0], check_interval_seconds=0
    )
    await index.search("vượt đèn đỏ", date(2025, 1, 1), 5)
    await index.search("vượt đèn đỏ", date(2025, 1, 1), 5)
    assert source.list_calls == 1
    source.hits.append(NEW)
    await index.search("vượt đèn đỏ", date(2025, 1, 1), 5)
    assert source.list_calls == 2
    now[0] = 120.0
    await index.search("vượt đèn đỏ", date(2025, 1, 1), 5)
    assert source.list_calls == 3


async def test_empty_corpus() -> None:
    index = LegalKeywordIndex(CountingSource([]), ttl_seconds=600)
    assert await index.search("luật", date(2026, 1, 1), 5) == []


class CountingCountSource(CountingSource):
    def __init__(self, hits) -> None:
        super().__init__(hits)
        self.count_calls = 0

    async def count_versions(self) -> int:
        self.count_calls += 1
        return await super().count_versions()


async def test_corpus_size_is_checked_at_most_once_per_interval() -> None:
    now = [0.0]
    source = CountingCountSource([OLD, FINE])
    index = LegalKeywordIndex(
        source, ttl_seconds=600, clock=lambda: now[0], check_interval_seconds=30
    )
    for _ in range(5):
        await index.search("vượt đèn đỏ", date(2025, 1, 1), 5)
    assert source.count_calls == 1
    now[0] = 31.0
    await index.search("vượt đèn đỏ", date(2025, 1, 1), 5)
    assert source.count_calls == 2


async def test_index_is_built_off_the_event_loop(monkeypatch) -> None:
    import threading

    from src.modules.legal.infrastructure import keyword_index

    threads: list[int] = []
    original = keyword_index.build_bm25_index

    def spy(versions):
        threads.append(threading.get_ident())
        return original(versions)

    monkeypatch.setattr(keyword_index, "build_bm25_index", spy)
    index = LegalKeywordIndex(CountingSource([OLD, FINE]), ttl_seconds=600)
    await index.search("đèn đỏ", date(2025, 1, 1), 5)
    assert threads and threads[0] != threading.get_ident()


async def test_stale_index_is_served_while_rebuilding() -> None:
    import asyncio

    release = asyncio.Event()

    class SlowSource(CountingSource):
        async def list_versions(self, provision_key=None):
            if self.list_calls >= 1:
                await release.wait()
            return await super().list_versions(provision_key)

    now = [0.0]
    source = SlowSource([OLD, FINE])
    index = LegalKeywordIndex(
        source, ttl_seconds=10, clock=lambda: now[0], check_interval_seconds=0
    )
    await index.search("vượt đèn đỏ", date(2025, 1, 1), 5)
    now[0] = 20.0
    rebuild = asyncio.create_task(index.search("vượt đèn đỏ", date(2025, 1, 1), 5))
    await asyncio.sleep(0)
    stale = await asyncio.wait_for(index.search("vượt đèn đỏ", date(2025, 1, 1), 5), timeout=1)
    assert [h.version_id for h in stale] == [FINE.version_id]
    release.set()
    await rebuild
