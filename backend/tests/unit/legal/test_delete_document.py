from datetime import datetime
from uuid import uuid4

import pytest

from kira.legal.errors import InvalidLegalDocumentStateError, LegalDocumentNotFoundError
from kira.legal.models import RelationType
from kira.legal.records import CandidateStatus, LegalDocumentStatus
from kira.legal.services.delete_document import DeleteLegalDocument
from tests.unit.legal.fakes import (
    FakeStorage,
    InMemoryLegalRepository,
    make_candidate,
    make_document,
)


class BrokenStorage(FakeStorage):
    async def delete(self, key: str) -> None:
        raise ConnectionError("minio down")


async def _setup(storage: FakeStorage | None = None):
    repository = InMemoryLegalRepository()
    storage = storage or FakeStorage()
    draft = make_document("31/2024/QH15", status=LegalDocumentStatus.FAILED)
    storage.objects[draft.file_key] = b"x"
    await repository.create_document(draft)
    amender = make_document("99/2026/QH15", status=LegalDocumentStatus.IN_REVIEW)
    await repository.create_document(amender)
    waiting = make_candidate(amender, RelationType.AMENDS, "31/2024/QH15", ref="D1", new_text="x")
    await repository.save_candidate(waiting)
    return DeleteLegalDocument(repository, storage), repository, storage, draft, waiting


async def test_delete_unpublished_document_removes_row_file_and_unresolves_dependents() -> None:
    service, repository, storage, draft, waiting = await _setup()
    await service.execute(draft.id)
    assert await repository.get_document(draft.id) is None
    assert storage.objects == {}
    reloaded = await repository.get_candidate(waiting.id)
    assert reloaded is not None and reloaded.status is CandidateStatus.UNRESOLVED_TARGET


async def test_previously_published_document_cannot_be_deleted() -> None:
    service, repository, _, draft, _ = await _setup()
    draft.published_at = datetime(2026, 1, 1, 8, 0)
    await repository.save_document(draft)
    with pytest.raises(InvalidLegalDocumentStateError):
        await service.execute(draft.id)
    assert await repository.get_document(draft.id) is not None


async def test_storage_failure_does_not_block_delete() -> None:
    service, repository, _, draft, _ = await _setup(BrokenStorage())
    await service.execute(draft.id)
    assert await repository.get_document(draft.id) is None


async def test_unknown_document_raises() -> None:
    service, _, _, _, _ = await _setup()
    with pytest.raises(LegalDocumentNotFoundError):
        await service.execute(uuid4())
