"""Upload a legal document file with admin-entered metadata."""

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID, uuid4

from kira.legal.errors import InvalidLegalDocumentInput, LegalDocumentConflict
from kira.legal.extraction.rules import DOCUMENT_NUMBER_PATTERN
from kira.legal.ports import LegalDocumentRepositoryPort
from kira.legal.records import (
    LegalDocumentMetadata,
    LegalDocumentRecord,
    LegalDocumentStatus,
)
from kira.providers.storage import MinioStorage

SUPPORTED_LEGAL_FILE_TYPES = frozenset({"pdf", "docx", "txt", "md", "html"})
LEGAL_DOCUMENT_TYPES = frozenset({"law", "decree", "circular", "decision", "resolution", "other"})


@dataclass(frozen=True)
class UploadLegalDocumentRequest:
    metadata: LegalDocumentMetadata
    file_name: str
    content: bytes
    content_type: str | None
    uploaded_by: UUID


class UploadLegalDocument:
    def __init__(self, repository: LegalDocumentRepositoryPort, storage: MinioStorage) -> None:
        self._repository = repository
        self._storage = storage

    async def execute(self, request: UploadLegalDocumentRequest) -> LegalDocumentRecord:
        file_type = _file_type(request.file_name)
        _validate(request, file_type)
        digest = sha256(request.content).hexdigest()
        number = request.metadata.number
        if await self._repository.get_document_by_number(number) is not None:
            raise LegalDocumentConflict(f"Legal document {number} already exists")
        if await self._repository.get_document_by_sha256(digest) is not None:
            raise LegalDocumentConflict("A legal document with identical content already exists")

        document_id = uuid4()
        file_key = f"legal/{document_id}.{file_type}"
        await self._storage.upload(
            key=file_key,
            data=request.content,
            content_type=request.content_type or "application/octet-stream",
        )
        record = LegalDocumentRecord(
            id=document_id,
            metadata=request.metadata,
            file_key=file_key,
            file_type=file_type,
            sha256=digest,
            status=LegalDocumentStatus.UPLOADED,
            uploaded_by=request.uploaded_by,
        )
        await self._repository.create_document(record)
        return record


def _file_type(file_name: str) -> str:
    return file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""


def _validate(request: UploadLegalDocumentRequest, file_type: str) -> None:
    metadata = request.metadata
    if DOCUMENT_NUMBER_PATTERN.fullmatch(metadata.number) is None:
        raise InvalidLegalDocumentInput(f"Invalid legal document number: {metadata.number}")
    if metadata.doc_type not in LEGAL_DOCUMENT_TYPES:
        raise InvalidLegalDocumentInput(f"Unsupported document type: {metadata.doc_type}")
    if not metadata.title.strip() or not metadata.issuer.strip():
        raise InvalidLegalDocumentInput("Title and issuer are required")
    if metadata.effective_date < metadata.issued_date:
        raise InvalidLegalDocumentInput("Effective date cannot be before the issued date")
    if file_type not in SUPPORTED_LEGAL_FILE_TYPES:
        raise InvalidLegalDocumentInput(f"Unsupported file type: {file_type or 'none'}")
    if not request.content:
        raise InvalidLegalDocumentInput("Uploaded file is empty")
