"""Admin API for the shared legal corpus."""

from collections.abc import Callable
from datetime import date
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.legal.api.dependencies import (
    LegalTaskEnqueuer,
    get_delete_service,
    get_provision_history_service,
    get_queries,
    get_review_service,
    get_task_enqueuer,
    get_upload_service,
)
from src.modules.legal.api.schemas import (
    CandidateReviewRequest,
    LegalDocumentResponse,
    ProvisionHistoryResponse,
    RelationCandidateResponse,
    ReviewResponse,
    TaskResponse,
)
from src.modules.legal.application.delete_document import DeleteLegalDocument
from src.modules.legal.application.errors import (
    InvalidLegalDocumentInput,
    InvalidLegalDocumentState,
    LegalDocumentConflict,
    LegalDocumentNotFound,
    LegalProvisionNotFound,
    RelationCandidateNotFound,
)
from src.modules.legal.application.provision_history import GetProvisionHistory
from src.modules.legal.application.queries import LegalDocumentQueries
from src.modules.legal.application.records import LegalDocumentMetadata, LegalDocumentStatus
from src.modules.legal.application.review_relation import ReviewDecision, ReviewRelationCandidate
from src.modules.legal.application.upload_document import (
    UploadLegalDocument,
    UploadLegalDocumentRequest,
)
from src.modules.legal.composition import vietnam_today
from src.shared.infrastructure.auth.dependencies import get_current_user, require_admin
from src.shared.infrastructure.persistence.database.models import User
from src.shared.infrastructure.persistence.database.session import get_session

router = APIRouter()

_ERROR_STATUS: dict[type[Exception], int] = {
    LegalDocumentNotFound: status.HTTP_404_NOT_FOUND,
    RelationCandidateNotFound: status.HTTP_404_NOT_FOUND,
    InvalidLegalDocumentState: status.HTTP_409_CONFLICT,
    LegalDocumentConflict: status.HTTP_409_CONFLICT,
    InvalidLegalDocumentInput: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _http_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=_ERROR_STATUS[type(exc)], detail=str(exc))


def _enqueue(task: Callable[[UUID], str], document_id: UUID) -> str:
    try:
        return task(document_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to enqueue legal task: {exc}",
        ) from exc


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_legal_document(
    file: UploadFile = File(...),
    number: str = Form(...),
    doc_type: str = Form(...),
    title: str = Form(...),
    issuer: str = Form(...),
    issued_date: date = Form(...),
    effective_date: date = Form(...),
    source_url: str | None = Form(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
    service: UploadLegalDocument = Depends(get_upload_service),
    enqueuer: LegalTaskEnqueuer = Depends(get_task_enqueuer),
) -> LegalDocumentResponse:
    request = UploadLegalDocumentRequest(
        metadata=LegalDocumentMetadata(
            number=number.strip(),
            doc_type=doc_type.strip(),
            title=title.strip(),
            issuer=issuer.strip(),
            issued_date=issued_date,
            effective_date=effective_date,
            source_url=source_url or None,
        ),
        file_name=file.filename or "",
        content=await file.read(),
        content_type=file.content_type,
        uploaded_by=current_user.id,
    )
    try:
        record = await service.execute(request)
    except (InvalidLegalDocumentInput, LegalDocumentConflict) as exc:
        raise _http_error(exc) from exc
    await db.commit()
    _enqueue(enqueuer.process, record.id)
    return LegalDocumentResponse.from_record(record)


@router.get("/documents")
async def list_legal_documents(
    document_status: LegalDocumentStatus | None = Query(None, alias="status"),
    _: User = Depends(require_admin),
    queries: LegalDocumentQueries = Depends(get_queries),
) -> list[LegalDocumentResponse]:
    documents = await queries.list_documents(document_status)
    return [LegalDocumentResponse.from_record(document) for document in documents]


@router.get("/documents/{document_id}")
async def get_legal_document(
    document_id: UUID,
    _: User = Depends(require_admin),
    queries: LegalDocumentQueries = Depends(get_queries),
) -> LegalDocumentResponse:
    try:
        return LegalDocumentResponse.from_record(await queries.get_document(document_id))
    except LegalDocumentNotFound as exc:
        raise _http_error(exc) from exc


@router.get("/documents/{document_id}/candidates")
async def list_relation_candidates(
    document_id: UUID,
    _: User = Depends(require_admin),
    queries: LegalDocumentQueries = Depends(get_queries),
) -> list[RelationCandidateResponse]:
    try:
        candidates = await queries.list_candidates(document_id)
    except LegalDocumentNotFound as exc:
        raise _http_error(exc) from exc
    return [RelationCandidateResponse.from_record(candidate) for candidate in candidates]


@router.patch("/candidates/{candidate_id}")
async def review_relation_candidate(
    candidate_id: UUID,
    body: CandidateReviewRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
    service: ReviewRelationCandidate = Depends(get_review_service),
    enqueuer: LegalTaskEnqueuer = Depends(get_task_enqueuer),
) -> ReviewResponse:
    decision = ReviewDecision(
        candidate_id=candidate_id,
        action=body.action,
        reviewer_id=current_user.id,
        note=body.note,
        target_number=body.target_number,
        target_provision_ref=body.target_provision_ref,
        effective_date=body.effective_date,
        new_text=body.new_text,
    )
    try:
        outcome = await service.execute(decision)
    except (
        RelationCandidateNotFound,
        InvalidLegalDocumentInput,
        InvalidLegalDocumentState,
    ) as exc:
        raise _http_error(exc) from exc
    await db.commit()
    task_id = (
        _enqueue(enqueuer.publish, outcome.republish_document_id)
        if outcome.republish_document_id is not None
        else None
    )
    return ReviewResponse(
        candidate=RelationCandidateResponse.from_record(outcome.candidate),
        republish_task_id=task_id,
    )


@router.post("/documents/{document_id}/publish", status_code=status.HTTP_202_ACCEPTED)
async def publish_legal_document(
    document_id: UUID,
    _: User = Depends(require_admin),
    queries: LegalDocumentQueries = Depends(get_queries),
    enqueuer: LegalTaskEnqueuer = Depends(get_task_enqueuer),
) -> TaskResponse:
    try:
        await queries.require_publishable(document_id)
    except (LegalDocumentNotFound, InvalidLegalDocumentState) as exc:
        raise _http_error(exc) from exc
    return TaskResponse(document_id=document_id, task_id=_enqueue(enqueuer.publish, document_id))


@router.post("/documents/{document_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_legal_document(
    document_id: UUID,
    _: User = Depends(require_admin),
    queries: LegalDocumentQueries = Depends(get_queries),
    enqueuer: LegalTaskEnqueuer = Depends(get_task_enqueuer),
) -> TaskResponse:
    try:
        await queries.require_processable(document_id)
    except (LegalDocumentNotFound, InvalidLegalDocumentState) as exc:
        raise _http_error(exc) from exc
    return TaskResponse(document_id=document_id, task_id=_enqueue(enqueuer.process, document_id))


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_legal_document(
    document_id: UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
    service: DeleteLegalDocument = Depends(get_delete_service),
) -> Response:
    try:
        await service.execute(document_id)
    except (LegalDocumentNotFound, InvalidLegalDocumentState) as exc:
        raise _http_error(exc) from exc
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/provisions")
async def get_provision_history(
    key: str = Query(..., min_length=3, max_length=160),
    day: date | None = Query(None, alias="date"),
    _: User = Depends(get_current_user),
    service: GetProvisionHistory = Depends(get_provision_history_service),
) -> ProvisionHistoryResponse:
    try:
        history = await service.execute(key, day or vietnam_today())
    except LegalProvisionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ProvisionHistoryResponse.from_history(history)
