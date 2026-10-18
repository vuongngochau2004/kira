"""Domain errors for the legal module."""

from collections.abc import Sequence


class LegalParseError(ValueError):
    """Raised when a legal document has no recognizable structure."""


class TimelineConflict(Exception):
    """Raised when approved changes cannot form a valid version timeline."""

    def __init__(self, change_ids: Sequence[str], reason: str) -> None:
        self.change_ids: tuple[str, ...] = tuple(change_ids)
        self.reason = reason
        super().__init__(f"Timeline conflict ({reason}): {', '.join(self.change_ids)}")
