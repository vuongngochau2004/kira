"""Legal corpus errors raised by services and domain rules; the router maps them to HTTP codes."""

from collections.abc import Sequence


class InvalidLegalDocumentInputError(ValueError):
    """Uploaded metadata, file, or review edit is invalid."""


class LegalDocumentConflictError(Exception):
    """A document with the same number or content already exists."""


class LegalDocumentNotFoundError(LookupError):
    """No legal document with the given id."""


class RelationCandidateNotFoundError(LookupError):
    """No relation candidate with the given id."""


class InvalidLegalDocumentStateError(Exception):
    """The requested operation is not allowed in the current state."""


class LegalTextExtractionError(Exception):
    """Text could not be extracted from the uploaded file."""


class LegalProvisionNotFoundError(LookupError):
    """No indexed versions for the given provision key."""


class LegalParseError(ValueError):
    """Raised when a legal document has no recognizable structure."""


class TimelineConflictError(Exception):
    """Raised when approved changes cannot form a valid version timeline."""

    def __init__(self, change_ids: Sequence[str], reason: str) -> None:
        self.change_ids: tuple[str, ...] = tuple(change_ids)
        self.reason = reason
        super().__init__(f"Timeline conflict ({reason}): {', '.join(self.change_ids)}")
