"""Celery implementation of the background-job port."""

from src.shared.ports.task_queue import TaskQueuePort
from src.worker.celery_app import celery_app


class CeleryTaskQueueAdapter(TaskQueuePort):
    """Adapt Celery task control for application services."""

    def revoke(self, task_id: str) -> None:
        celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")


__all__ = ["CeleryTaskQueueAdapter"]
