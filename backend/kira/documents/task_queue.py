"""Celery implementation of the background-job port."""

from kira.documents.task_queue_port import TaskQueuePort
from kira.worker import celery_app


class CeleryTaskQueueAdapter(TaskQueuePort):
    """Adapt Celery task control for application services."""

    def revoke(self, task_id: str) -> None:
        celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")


__all__ = ["CeleryTaskQueueAdapter"]
