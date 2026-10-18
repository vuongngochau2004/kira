from dataclasses import replace
from datetime import date, datetime

from src.modules.legal.application.records import CandidateStatus, LegalDocumentStatus
from src.modules.legal.domain.models import RelationType
from src.modules.legal.infrastructure.repositories import (
    apply_candidate,
    apply_document,
    candidate_from_model,
    candidate_to_model,
    document_from_model,
    document_to_model,
)
from tests.legal_fakes import ADMIN_ID, make_candidate, make_document

TEXT = "Điều 1. Phạm vi\nNội dung."


def test_document_round_trip() -> None:
    record = make_document("31/2024/QH15", status=LegalDocumentStatus.IN_REVIEW, text=TEXT)
    record.warnings = ["unbalanced_quotes"]
    model = document_to_model(record)
    assert model.number == "31/2024/QH15"
    assert model.status == "in_review"
    restored = document_from_model(model)
    assert restored == replace(record, created_at=None)


def test_apply_document_updates_mutable_fields() -> None:
    record = make_document("31/2024/QH15", status=LegalDocumentStatus.IN_REVIEW, text=TEXT)
    model = document_to_model(record)
    record.status = LegalDocumentStatus.PUBLISHED
    record.published_at = datetime(2026, 7, 1, 9, 0)
    record.error_detail = None
    apply_document(model, record)
    assert model.status == "published"
    assert model.published_at == datetime(2026, 7, 1, 9, 0)


def test_candidate_round_trip() -> None:
    source = make_document("99/2026/QH15", effective_date=date(2026, 7, 1))
    record = make_candidate(
        source,
        RelationType.AMENDS,
        "31/2024/QH15",
        ref="D3.K1",
        new_text="1. Mới.",
        source_key="99/2026/QH15#D1.K1",
        status=CandidateStatus.APPROVED,
    )
    record.reviewed_by = ADMIN_ID
    record.reviewed_at = datetime(2026, 6, 1, 8, 0)
    record.flags = ["edited"]
    model = candidate_to_model(record)
    assert model.type == "AMENDS"
    assert model.status == "approved"
    assert candidate_from_model(model) == record

    record.status = CandidateStatus.REJECTED
    apply_candidate(model, record)
    assert model.status == "rejected"


def test_published_keys_round_trip() -> None:
    record = make_document("99/2026/QH15", text=TEXT)
    record.published_keys = ["31/2024/QH15#D3.K1"]
    assert document_from_model(document_to_model(record)).published_keys == ["31/2024/QH15#D3.K1"]
