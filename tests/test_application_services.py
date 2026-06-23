"""Component tests for application services using in-memory ports."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.modules.chat.application.citations import EnrichCitations
from src.modules.document.application.dto import GetDocumentChunksRequest
from src.modules.document.application.query import GetDocumentChunks
from src.modules.identity.application.service import IdentityService


class FakeUsers:
    def __init__(self):
        self.users = {}

    async def get_by_email(self, email):
        return self.users.get(email)

    async def get_active_by_id(self, user_id):
        return next((user for user in self.users.values() if str(user.id) == user_id and user.is_active), None)

    async def create(self, *, email, hashed_password, full_name):
        user = SimpleNamespace(id=uuid4(), email=email, hashed_password=hashed_password, full_name=full_name, is_active=True)
        self.users[email] = user
        return user


class FakeDocuments:
    def __init__(self):
        self.calls = []

    async def get_filenames(self, document_ids):
        self.calls.append(document_ids)
        return {document_ids[0]: "quy-che.pdf"}


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
async def test_identity_register_authenticate_and_active_lookup():
    service = IdentityService(FakeUsers(), lambda password: f"hash:{password}", lambda raw, hashed: hashed == f"hash:{raw}")
    user = await service.register(email="a@example.com", password="secret", full_name="A")

    assert (await service.authenticate(email="a@example.com", password="secret")).id == user.id
    assert await service.authenticate(email="a@example.com", password="wrong") is None
    assert (await service.get_active_user(str(user.id))).email == "a@example.com"
    with pytest.raises(ValueError, match="already registered"):
        await service.register(email="a@example.com", password="secret", full_name="A")


@pytest.mark.asyncio
async def test_citation_enrichment_preserves_unknown_citations():
    port = FakeDocuments()
    citations = [{"document_id": "doc-1"}, {"filename": "already-known.pdf"}]

    result = await EnrichCitations(port).execute(citations)

    assert port.calls == [["doc-1"]]
    assert result[0]["filename"] == "quy-che.pdf"
    assert result[1]["filename"] == "already-known.pdf"


@pytest.mark.asyncio
async def test_document_chunks_enforce_owner_scope():
    owner_id = uuid4()
    repository = FakeDocumentRepository(SimpleNamespace(id=uuid4(), user_id=owner_id))
    service = GetDocumentChunks(repository)

    denied = await service.execute(GetDocumentChunksRequest(document_id=repository.document.id, user_id=uuid4()))
    allowed = await service.execute(GetDocumentChunksRequest(document_id=repository.document.id, user_id=owner_id))

    assert denied is None
    assert allowed is not None
    assert repository.requested_user_id == owner_id
