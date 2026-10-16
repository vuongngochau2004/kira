from datetime import date
from uuid import uuid4

from src.modules.legal.application.records import (
    CandidateStatus,
    RelationCandidateRecord,
)
from src.modules.legal.application.serialization import provisions_from_json, provisions_to_json
from src.modules.legal.domain.models import ProvisionLevel, RelationType
from src.modules.legal.domain.parser import parse_legal_structure

TEXT = """Điều 2. Giải thích từ ngữ
1. Chủ sử dụng đất bao gồm:
a) Cá nhân trong nước;
"""


def test_provisions_round_trip_through_json() -> None:
    provisions = parse_legal_structure(TEXT, "31/2024/QH15").provisions
    rows = provisions_to_json(provisions)
    assert rows[2] == {
        "provision_key": "31/2024/QH15#D2.K1.a",
        "level": "point",
        "label": "Điểm a",
        "heading": "",
        "chapter_label": None,
        "text": "a) Cá nhân trong nước;",
        "page": None,
        "parent_key": "31/2024/QH15#D2.K1",
    }
    restored = provisions_from_json(rows)
    assert tuple(restored) == provisions
    assert restored[0].level is ProvisionLevel.ARTICLE


def test_candidate_target_key() -> None:
    candidate = RelationCandidateRecord(
        id=uuid4(),
        legal_document_id=uuid4(),
        type=RelationType.AMENDS,
        target_number="31/2024/QH15",
        evidence_text="x",
        confidence=0.7,
        extractor="rule",
        status=CandidateStatus.PENDING,
        effective_date=date(2026, 7, 1),
        target_provision_ref="D3.K1",
    )
    assert candidate.target_provision_key == "31/2024/QH15#D3.K1"
    candidate.target_provision_ref = None
    assert candidate.target_provision_key is None
