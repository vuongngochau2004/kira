from datetime import date
from uuid import uuid4

import pytest

from src.modules.legal.application.errors import (
    InvalidLegalDocumentInput,
    InvalidLegalDocumentState,
    RelationCandidateNotFound,
)
from src.modules.legal.application.records import CandidateStatus, LegalDocumentStatus
from src.modules.legal.application.review_relation import ReviewDecision, ReviewRelationCandidate
from src.modules.legal.domain.models import RelationType
from tests.legal_fakes import ADMIN_ID, InMemoryLegalRepository, make_candidate, make_document


async def _setup(source_status: LegalDocumentStatus = LegalDocumentStatus.IN_REVIEW, **kwargs):
    repository = InMemoryLegalRepository()
    target = make_document("31/2024/QH15")
    source = make_document("99/2026/QH15", status=source_status, effective_date=date(2026, 7, 1))
    await repository.create_document(target)
    await repository.create_document(source)
    candidate = make_candidate(
        source,
        RelationType.AMENDS,
        "31/2024/QH15",
        ref="D3.K1",
        new_text="1. Nội dung mới.",
        status=kwargs.get("status", CandidateStatus.PENDING),
    )
    await repository.save_candidate(candidate)
    return ReviewRelationCandidate(repository), repository, source, candidate


async def test_approve_sets_reviewer_and_needs_no_republish_before_publish() -> None:
    service, repository, _, candidate = await _setup()
    outcome = await service.execute(ReviewDecision(candidate.id, "approve", ADMIN_ID, note="Đúng"))
    assert outcome.candidate.status is CandidateStatus.APPROVED
    assert outcome.candidate.reviewed_by == ADMIN_ID
    assert outcome.candidate.reviewed_at is not None
    assert outcome.candidate.review_note == "Đúng"
    assert outcome.republish_document_id is None
    stored = await repository.get_candidate(candidate.id)
    assert stored is not None and stored.status is CandidateStatus.APPROVED


async def test_approving_on_published_source_requests_republish() -> None:
    service, _, source, candidate = await _setup(LegalDocumentStatus.PUBLISHED)
    outcome = await service.execute(ReviewDecision(candidate.id, "approve", ADMIN_ID))
    assert outcome.republish_document_id == source.id


async def test_rejecting_previously_approved_on_published_source_requests_republish() -> None:
    service, _, source, candidate = await _setup(
        LegalDocumentStatus.PUBLISHED, status=CandidateStatus.APPROVED
    )
    outcome = await service.execute(ReviewDecision(candidate.id, "reject", ADMIN_ID))
    assert outcome.candidate.status is CandidateStatus.REJECTED
    assert outcome.republish_document_id == source.id


async def test_rejecting_pending_on_published_source_needs_no_republish() -> None:
    service, _, _, candidate = await _setup(LegalDocumentStatus.PUBLISHED)
    outcome = await service.execute(ReviewDecision(candidate.id, "reject", ADMIN_ID))
    assert outcome.republish_document_id is None


async def test_edit_updates_fields_and_resets_to_pending() -> None:
    service, _, _, candidate = await _setup(status=CandidateStatus.APPROVED)
    outcome = await service.execute(
        ReviewDecision(
            candidate.id,
            "edit",
            ADMIN_ID,
            target_provision_ref="D3.K2",
            effective_date=date(2026, 8, 1),
            new_text=" 2. Nội dung đã sửa. ",
        )
    )
    assert outcome.candidate.status is CandidateStatus.PENDING
    assert outcome.candidate.target_provision_ref == "D3.K2"
    assert outcome.candidate.effective_date == date(2026, 8, 1)
    assert outcome.candidate.new_text == "2. Nội dung đã sửa."


async def test_edit_to_unknown_target_marks_unresolved() -> None:
    service, _, _, candidate = await _setup()
    outcome = await service.execute(
        ReviewDecision(candidate.id, "edit", ADMIN_ID, target_number="45/2013/QH13")
    )
    assert outcome.candidate.status is CandidateStatus.UNRESOLVED_TARGET


@pytest.mark.parametrize(
    "fields",
    [
        {"target_number": "Luật cũ"},
        {"target_provision_ref": "Điều 3"},
        {"new_text": "   "},
    ],
)
async def test_invalid_edits_are_rejected(fields: dict) -> None:
    service, _, _, candidate = await _setup()
    with pytest.raises(InvalidLegalDocumentInput):
        await service.execute(ReviewDecision(candidate.id, "edit", ADMIN_ID, **fields))


async def test_approve_requires_known_target() -> None:
    service, repository, _, candidate = await _setup()
    candidate.target_number = "45/2013/QH13"
    candidate.status = CandidateStatus.UNRESOLVED_TARGET
    await repository.save_candidate(candidate)
    with pytest.raises(InvalidLegalDocumentState):
        await service.execute(ReviewDecision(candidate.id, "approve", ADMIN_ID))


async def test_approve_amendment_requires_ref_and_text() -> None:
    service, repository, _, candidate = await _setup()
    candidate.new_text = None
    await repository.save_candidate(candidate)
    with pytest.raises(InvalidLegalDocumentInput):
        await service.execute(ReviewDecision(candidate.id, "approve", ADMIN_ID))


async def test_unknown_candidate_raises() -> None:
    service, _, _, _ = await _setup()
    with pytest.raises(RelationCandidateNotFound):
        await service.execute(ReviewDecision(uuid4(), "approve", ADMIN_ID))
