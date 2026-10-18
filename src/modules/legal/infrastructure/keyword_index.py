"""In-process BM25 index of the legal corpus, rebuilt from the Qdrant collection.

The BM25 manager of the retrieval module is per user and in memory, so a Celery worker cannot
update the API process's index. This index rebuilds itself when the corpus size changes or its
TTL expires (an edited amendment keeps the size unchanged). Rebuilds run in a worker thread and
requests keep using the previous index meanwhile, so tokenizing a large corpus never blocks the
event loop.
"""

import asyncio
import time
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import date

from src.modules.legal.application.ports import LegalKeywordSearchPort, LegalProvisionSearchPort
from src.modules.legal.domain.qa import ProvisionHit
from src.modules.retrieval.domain.services.bm25 import BM25Index


def build_bm25_index(versions: Sequence[ProvisionHit]) -> BM25Index:
    index = BM25Index()
    index.index_documents(
        [
            {
                "content": f"{hit.label} {hit.title} {hit.text}",
                "metadata": {"version_id": hit.version_id},
            }
            for hit in versions
        ]
    )
    return index


class LegalKeywordIndex(LegalKeywordSearchPort):
    def __init__(
        self,
        source: LegalProvisionSearchPort,
        ttl_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        check_interval_seconds: float = 30.0,
    ) -> None:
        self._source = source
        self._ttl = ttl_seconds
        self._clock = clock
        self._check_interval = check_interval_seconds
        self._index: BM25Index | None = None
        self._hits: dict[str, ProvisionHit] = {}
        self._built_count = -1
        self._built_at = 0.0
        self._checked_at = float("-inf")
        self._lock = asyncio.Lock()

    async def search(self, query: str, day: date, limit: int) -> list[ProvisionHit]:
        await self._maybe_refresh()
        index, hits_by_id = self._index, self._hits
        if index is None:
            return []
        results: list[ProvisionHit] = []
        for item in index.search(query, k=max(limit * 5, limit)):
            if item["score"] <= 0:
                continue
            hit = hits_by_id.get(str(item["metadata"].get("version_id")))
            if hit is not None and hit.in_force_on(day):
                results.append(replace(hit, score=float(item["score"])))
            if len(results) >= limit:
                break
        return results

    async def _maybe_refresh(self) -> None:
        if self._index is not None and (
            self._lock.locked() or self._clock() - self._checked_at < self._check_interval
        ):
            return  # serve the current index: checked recently, or another request rebuilds it
        async with self._lock:
            now = self._clock()
            if self._index is not None and now - self._checked_at < self._check_interval:
                return
            self._checked_at = now
            count = await self._source.count_versions()
            if self._built_count == count and now - self._built_at < self._ttl:
                return
            versions = await self._source.list_versions()
            index = await asyncio.to_thread(build_bm25_index, versions) if versions else None
            self._index = index
            self._hits = {hit.version_id: hit for hit in versions}
            self._built_count = count
            self._built_at = now
