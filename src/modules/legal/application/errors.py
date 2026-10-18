"""Application-level errors of the legal module."""


class InvalidLegalDocumentInput(ValueError):
    """Uploaded metadata, file, or review edit is invalid."""


class LegalDocumentConflict(Exception):
    """A document with the same number or content already exists."""


class LegalDocumentNotFound(LookupError):
    """No legal document with the given id."""


class RelationCandidateNotFound(LookupError):
    """No relation candidate with the given id."""


class InvalidLegalDocumentState(Exception):
    """The requested operation is not allowed in the current state."""


class LegalTextExtractionError(Exception):
    """Text could not be extracted from the uploaded file."""


class LegalProvisionNotFound(LookupError):
    """No indexed versions for the given provision key."""
