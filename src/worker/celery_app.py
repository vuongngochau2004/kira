"""Celery application configuration."""

from celery import Celery

from src.config.config import settings


celery_app = Celery(
    "kira",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.worker.document_tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    task_always_eager=settings.celery_task_always_eager,
)

__all__ = ["celery_app"]

