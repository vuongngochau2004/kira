"""Abstract base class for repositories.

Repositories provide a collection-like interface for accessing
domain entities from persistence layer, following the Repository
pattern from Domain-Driven Design.

Example:
    >>> from src.shared.kernel.base.repository import Repository
    >>> from uuid import UUID
    >>>
    >>> class DocumentRepository(Repository[Document]):
    ...     async def find_by_id(self, id: UUID) -> Document | None:
    ...         ...
    ...     async def save(self, entity: Document) -> None:
    ...         ...
    ...     async def delete(self, id: UUID) -> None:
    ...         ...
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional
from uuid import UUID

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Abstract base class for all repositories.

    Repositories abstract the persistence layer, providing
    a domain-oriented interface for querying and persisting entities.
    They decouple domain logic from infrastructure concerns (DIP).

    Type Parameters:
        T: The entity type this repository manages.
    """

    @abstractmethod
    async def find_by_id(self, id: UUID) -> Optional[T]:
        """Find an entity by its unique identifier.

        Args:
            id: The unique identifier of the entity.

        Returns:
            The entity if found, None otherwise.
        """
        raise NotImplementedError("Subclasses must implement find_by_id()")

    @abstractmethod
    async def save(self, entity: T) -> None:
        """Persist an entity (create or update).

        Args:
            entity: The entity to persist.
        """
        raise NotImplementedError("Subclasses must implement save()")

    @abstractmethod
    async def delete(self, id: UUID) -> None:
        """Delete an entity by its unique identifier.

        Args:
            id: The unique identifier of the entity to delete.
        """
        raise NotImplementedError("Subclasses must implement delete()")