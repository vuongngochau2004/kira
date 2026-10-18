"""Opt-in repository contract test against the docker-compose PostgreSQL."""

import os
from uuid import uuid4

import pytest

from src.modules.legal.application.records import CandidateStatus, LegalDocumentStatus
from src.modules.legal.domain.models import RelationType
from src.modules.legal.infrastructure.repositories import SqlAlchemyLegalRepository
from src.shared.infrastructure.persistence.database.models import User
from src.shared.infrastructure.persistence.database.session import async_session_factory, init_db
from tests.legal_fakes import make_candidate, make_document

pytestmark = pytest.mark.integration


async def test_legal_repository_round_trip() -> None:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("Set RUN_INTEGRATION=1 with Docker services running")

    await init_db()
    async with async_session_factory() as session:
        user = User(
            email=f"legal-{uuid4().hex}@example.com",
            hashed_password="x",
            full_name="Legal Test",
            role="admin",
        )
        session.add(user)
        await session.flush()
        repository = SqlAlchemyLegalRepository(session)

        suffix = uuid4().hex[:6].upper()
        base = make_document(f"1/2099/QH{suffix}", text="Điều 1. Phạm vi\nNội dung.")
        base.uploaded_by = user.id
        amending = make_document(f"2/2099/QH{suffix}", status=LegalDocumentStatus.IN_REVIEW)
        amending.uploaded_by = user.id
        await repository.create_document(base)
        await repository.create_document(amending)

        assert (await repository.get_document_by_number(base.metadata.number)).id == base.id
        assert (await repository.get_document_by_sha256(base.sha256)).id == base.id

        candidate = make_candidate(
            amending,
            RelationType.AMENDS,
            base.metadata.number,
            ref="D1",
            new_text="Điều 1. Mới.",
            status=CandidateStatus.PENDING,
        )
        await repository.replace_candidates(amending.id, [candidate])
        candidate.status = CandidateStatus.APPROVED
        await repository.save_candidate(candidate)
        targeting = await repository.list_candidates_targeting(
            base.metadata.number, [CandidateStatus.APPROVED]
        )
        assert [c.id for c in targeting] == [candidate.id]

        amending.status = LegalDocumentStatus.PUBLISHED
        await repository.save_document(amending)
        published = await repository.list_documents(LegalDocumentStatus.PUBLISHED)
        assert {d.id for d in published} >= {base.id, amending.id}

        await repository.acquire_publish_lock()
        await repository.replace_candidates(amending.id, [candidate])
        await repository.delete_document(amending.id)
        assert await repository.get_document(amending.id) is None
        assert await repository.list_candidates(amending.id) == []
        await session.rollback()
