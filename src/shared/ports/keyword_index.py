"""Port: keyword index contract."""

from abc import ABC, abstractmethod
from uuid import UUID


class KeywordIndexPort(ABC):
    """Keyword index operations required by application services."""

    @abstractmethod
    async def add_document_bulk(self, user_id: UUID | str, chunks: list[dict]) -> None:
        """Add document chunks to the user's keyword index."""
        ...

    @abstractmethod
    async def remove_document(self, user_id: UUID | str, document_id: UUID | str) -> None:
        """Remove a document from the user's keyword index."""
        ...


__all__ = ["KeywordIndexPort"]
