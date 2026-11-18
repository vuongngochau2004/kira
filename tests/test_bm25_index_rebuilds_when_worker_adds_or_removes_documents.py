"""The API process's BM25 index must follow documents processed by the Celery worker.

The worker chunks documents in another process, so its in-memory index updates never reach the
API. Before this fix the API built a user's index once (when empty) and never picked up
documents completed later: a 38-page PDF stayed invisible to keyword search.
"""

from typing import Any
from uuid import uuid4

import pytest

from src.modules.retrieval.application.search_use_case import SearchUseCase
from src.modules.retrieval.infrastructure.keyword.bm25_manager import BM25IndexManager
from src.modules.retrieval.infrastructure.retrieval_adapters import BM25KeywordSearchAdapter


class FakeDocuments:
    """Persisted chunks as the worker leaves them in Postgres."""

    def __init__(self) -> None:
        self.chunks: list[dict[str, Any]] = []
        self.version = 0
        self.list_calls = 0

    def add_document(self, *contents: str) -> None:
        doc_id = str(uuid4())
        for i, content in enumerate(contents):
            self.chunks.append(
                {"index": i, "content": content, "metadata": {"document_id": doc_id}}
            )
        self.version += 1

    def remove_all(self) -> None:
        self.chunks = []
        self.version += 1

    async def completed_chunks_signature(self, user_id) -> tuple[int, int]:
        return (self.version, len(self.chunks))

    async def list_completed_chunks(self, user_id) -> list[dict[str, Any]]:
        self.list_calls += 1
        return list(self.chunks)

    async def get_filenames(self, document_ids: list[str]) -> dict[str, str]:
        return {}


@pytest.fixture
def setup() -> tuple[SearchUseCase, BM25IndexManager, FakeDocuments, str]:
    manager = BM25IndexManager()
    documents = FakeDocuments()
    use_case = SearchUseCase(
        vector_store=None,  # type: ignore[arg-type] - dense search is not exercised here
        keyword_search=BM25KeywordSearchAdapter(manager),
        documents=documents,
    )
    return use_case, manager, documents, str(uuid4())


@pytest.mark.asyncio
async def test_document_completed_after_first_build_is_indexed(setup) -> None:
    use_case, manager, documents, user_id = setup
    documents.add_document("quy chế đào tạo tín chỉ")
    await use_case._ensure_bm25_index(user_id)
    assert manager.get_index(user_id).document_count == 1

    # Worker finishes a second document in another process.
    documents.add_document("đồ án tốt nghiệp quyết định 209", "liêm chính học thuật")
    await use_case._ensure_bm25_index(user_id)

    assert manager.get_index(user_id).document_count == 3


@pytest.mark.asyncio
async def test_unchanged_corpus_does_not_rebuild(setup) -> None:
    use_case, _, documents, user_id = setup
    documents.add_document("quy chế đào tạo tín chỉ")

    await use_case._ensure_bm25_index(user_id)
    await use_case._ensure_bm25_index(user_id)
    await use_case._ensure_bm25_index(user_id)

    assert documents.list_calls == 1


@pytest.mark.asyncio
async def test_deleting_every_document_empties_the_index(setup) -> None:
    use_case, manager, documents, user_id = setup
    documents.add_document("quy chế đào tạo tín chỉ")
    await use_case._ensure_bm25_index(user_id)

    documents.remove_all()
    await use_case._ensure_bm25_index(user_id)

    assert not manager.has_documents(user_id)


@pytest.mark.asyncio
async def test_remove_document_forces_rebuild_of_remaining_chunks(setup) -> None:
    use_case, manager, documents, user_id = setup
    documents.add_document("quy chế đào tạo tín chỉ", "học phần bắt buộc")
    await use_case._ensure_bm25_index(user_id)

    # delete.py calls remove_document, which clears the whole in-memory index.
    manager.remove_document(user_id, "any-document")
    assert manager.get_signature(user_id) is None
    await use_case._ensure_bm25_index(user_id)

    assert manager.get_index(user_id).document_count == 2
