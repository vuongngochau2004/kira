"""Celery tasks for document processing."""

from __future__ import annotations

import asyncio
import logging
import uuid

from src.modules.document.application import ProcessDocumentRequest
from src.modules.document.composition import process_document_service
from src.shared.infrastructure.persistence.database.session import async_session_factory
from src.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="documents.process",
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def process_document_task(
    self,
    document_id: str,
    user_id: str,
    storage_path: str,
    timeout_seconds: int = 600,
) -> dict:
    """Process one uploaded document in a Celery worker."""
    logger.info(
        "Celery document task started task_id=%s document_id=%s user_id=%s storage_path=%s",
        self.request.id,
        document_id,
        user_id,
        storage_path,
    )
    result = asyncio.run(
        _process_document_async(
            document_id=document_id,
            user_id=user_id,
            storage_path=storage_path,
            timeout_seconds=timeout_seconds,
        )
    )
    logger.info(
        "Celery document task finished task_id=%s document_id=%s success=%s chunk_count=%s error=%s",
        self.request.id,
        document_id,
        result.get("success"),
        result.get("chunk_count"),
        result.get("error"),
    )
    return result


async def _process_document_async(
    *,
    document_id: str,
    user_id: str,
    storage_path: str,
    timeout_seconds: int,
) -> dict:
    """Open a worker-local DB session and run the existing process service."""
    async with async_session_factory() as session:
        result = await process_document_service(session).execute(
            ProcessDocumentRequest(
                document_id=uuid.UUID(document_id),
                user_id=uuid.UUID(user_id),
                storage_path=storage_path,
                timeout_seconds=timeout_seconds,
            )
        )
        await session.commit()
        return {
            "document_id": str(result.document_id),
            "success": result.success,
            "chunk_count": result.chunk_count,
            "error": result.error,
        }


__all__ = ["process_document_task"]

