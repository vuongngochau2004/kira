"""Tests for kira.documents.queries."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from kira.documents.queries import GetDocumentChunks
from kira.documents.schemas import GetDocumentChunksRequest


class FakeDocumentRepository:
    def __init__(self, document):
        self.document = document
        self.requested_user_id = None

    async def get_document(self, document_id, user_id=None):
        self.requested_user_id = user_id
        return self.document if user_id == self.document.user_id else None

    async def get_document_chunks(self, document_id):
        return [SimpleNamespace(id=uuid4(), content="chunk")]


@pytest.mark.asyncio
async def test_document_chunks_enforce_owner_scope():
    owner_id = uuid4()
    repository = FakeDocumentRepository(SimpleNamespace(id=uuid4(), user_id=owner_id))
    service = GetDocumentChunks(repository)

    denied = await service.execute(
        GetDocumentChunksRequest(document_id=repository.document.id, user_id=uuid4())
    )
    allowed = await service.execute(
        GetDocumentChunksRequest(document_id=repository.document.id, user_id=owner_id)
    )

    assert denied is None
    assert allowed is not None
    assert repository.requested_user_id == owner_id
