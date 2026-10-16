"""Celery tasks for the legal knowledge graph."""

from __future__ import annotations

import logging
import uuid

from src.modules.legal.composition import (
    legal_graph,
    process_legal_document_service,
    publish_legal_document_service,
)
from src.shared.infrastructure.persistence.database.session import async_session_factory
from src.worker.celery_app import celery_app
from src.worker.event_loop import get_worker_event_loop

logger = logging.getLogger(__name__)

_RETRY_OPTIONS = {
    "bind": True,
    "autoretry_for": (ConnectionError, TimeoutError),
    "retry_backoff": True,
    "retry_jitter": True,
    "retry_kwargs": {"max_retries": 3},
}


@celery_app.task(name="legal.process", **_RETRY_OPTIONS)
def process_legal_document_task(self, document_id: str) -> dict:
    logger.info("Processing legal document %s", document_id)
    return get_worker_event_loop().run_until_complete(run_process(document_id))


@celery_app.task(name="legal.publish", **_RETRY_OPTIONS)
def publish_legal_document_task(self, document_id: str) -> dict:
    logger.info("Publishing legal document %s", document_id)
    result = get_worker_event_loop().run_until_complete(run_publish(document_id))
    for dependent_id in result["republish_ids"]:
        publish_legal_document_task.delay(dependent_id)
    return result


async def run_process(document_id: str) -> dict:
    async with async_session_factory() as session:
        record = await process_legal_document_service(session).execute(uuid.UUID(document_id))
        await session.commit()
    return _result(document_id, record)


async def run_publish(document_id: str) -> dict:
    graph = legal_graph()
    try:
        async with async_session_factory() as session:
            service = publish_legal_document_service(session, graph)
            outcome = await service.execute(uuid.UUID(document_id))
            await session.commit()
    finally:
        await graph.close()
    result = _result(document_id, outcome.document)
    result["republish_ids"] = [str(dependent) for dependent in outcome.republish_document_ids]
    return result


def _result(document_id: str, record) -> dict:
    return {
        "document_id": document_id,
        "status": record.status.value,
        "error": record.error_detail,
    }
