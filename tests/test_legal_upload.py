from dataclasses import replace
from datetime import date

import pytest

from src.modules.legal.application.errors import InvalidLegalDocumentInput, LegalDocumentConflict
from src.modules.legal.application.records import LegalDocumentMetadata, LegalDocumentStatus
from src.modules.legal.application.upload_document import (
    UploadLegalDocument,
    UploadLegalDocumentRequest,
)
from tests.legal_fakes import ADMIN_ID, FakeStorage, InMemoryLegalRepository

METADATA = LegalDocumentMetadata(
    number="31/2024/QH15",
    doc_type="law",
    title="Luật Đất đai",
    issuer="Quốc hội",
    issued_date=date(2024, 1, 18),
    effective_date=date(2024, 8, 1),
    source_url="https://vbpl.vn/example",
)


def _request(**overrides) -> UploadLegalDocumentRequest:
    request = UploadLegalDocumentRequest(
        metadata=METADATA,
        file_name="luat-dat-dai.PDF",
        content=b"%PDF-1.7 content",
        content_type="application/pdf",
        uploaded_by=ADMIN_ID,
    )
    return replace(request, **overrides)


@pytest.fixture
def service() -> tuple[UploadLegalDocument, InMemoryLegalRepository, FakeStorage]:
    repository = InMemoryLegalRepository()
    storage = FakeStorage()
    return UploadLegalDocument(repository, storage), repository, storage


async def test_upload_stores_file_and_creates_uploaded_record(service) -> None:
    upload, repository, storage = service
    record = await upload.execute(_request())
    assert record.status is LegalDocumentStatus.UPLOADED
    assert record.file_type == "pdf"
    assert record.file_key == f"legal/{record.id}.pdf"
    assert storage.objects[record.file_key] == b"%PDF-1.7 content"
    stored = await repository.get_document(record.id)
    assert stored is not None
    assert stored.metadata == METADATA
    assert len(stored.sha256) == 64


async def test_duplicate_number_or_content_conflicts(service) -> None:
    upload, _, _ = service
    await upload.execute(_request())
    with pytest.raises(LegalDocumentConflict):
        await upload.execute(_request(content=b"different bytes"))
    other = replace(METADATA, number="32/2024/QH15")
    with pytest.raises(LegalDocumentConflict):
        await upload.execute(_request(metadata=other))


@pytest.mark.parametrize(
    "overrides",
    [
        {"metadata": replace(METADATA, number="Luật đất đai")},
        {"metadata": replace(METADATA, doc_type="memo")},
        {"metadata": replace(METADATA, title="  ")},
        {"metadata": replace(METADATA, effective_date=date(2023, 1, 1))},
        {"file_name": "law.exe"},
        {"file_name": "no-extension"},
        {"content": b""},
    ],
)
async def test_invalid_input_is_rejected_before_storage(service, overrides) -> None:
    upload, repository, storage = service
    with pytest.raises(InvalidLegalDocumentInput):
        await upload.execute(_request(**overrides))
    assert storage.objects == {}
    assert repository.documents == {}
