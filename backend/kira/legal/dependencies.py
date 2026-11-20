"""FastAPI dependency providers for the legal API."""

from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from kira.db.session import get_session
from kira.deps import (
    delete_legal_document_service,
    ingest_legal_from_url_service,
    legal_queries,
    legal_search_index,
    review_relation_service,
    upload_legal_document_service,
)
from kira.legal.services.delete_document import DeleteLegalDocument
from kira.legal.services.ingest_from_url import IngestLegalFromUrl
from kira.legal.services.provision_history import GetProvisionHistory
from kira.legal.services.queries import LegalDocumentQueries
from kira.legal.services.review_relation import ReviewRelationCandidate
from kira.legal.services.upload_document import UploadLegalDocument


def get_upload_service(db: AsyncSession = Depends(get_session)) -> UploadLegalDocument:
    return upload_legal_document_service(db)


def get_ingest_from_url_service(db: AsyncSession = Depends(get_session)) -> IngestLegalFromUrl:
    return ingest_legal_from_url_service(db)


def get_review_service(db: AsyncSession = Depends(get_session)) -> ReviewRelationCandidate:
    return review_relation_service(db)


def get_delete_service(db: AsyncSession = Depends(get_session)) -> DeleteLegalDocument:
    return delete_legal_document_service(db)


def get_queries(db: AsyncSession = Depends(get_session)) -> LegalDocumentQueries:
    return legal_queries(db)


class LegalTaskEnqueuer:
    """Enqueue legal Celery tasks without importing Celery at app startup."""

    def process(self, document_id: UUID) -> str:
        from kira.legal.tasks import process_legal_document_task

        return str(process_legal_document_task.delay(str(document_id)).id)

    def publish(self, document_id: UUID) -> str:
        from kira.legal.tasks import publish_legal_document_task

        return str(publish_legal_document_task.delay(str(document_id)).id)


def get_task_enqueuer() -> LegalTaskEnqueuer:
    return LegalTaskEnqueuer()


def get_provision_history_service() -> GetProvisionHistory:
    return GetProvisionHistory(legal_search_index())
