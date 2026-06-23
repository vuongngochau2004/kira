"""Port for background job control."""

from abc import ABC, abstractmethod


class TaskQueuePort(ABC):
    """Background-job operations required by application services."""

    @abstractmethod
    def revoke(self, task_id: str) -> None:
        """Request cancellation of a queued or running task."""
        ...


__all__ = ["TaskQueuePort"]
