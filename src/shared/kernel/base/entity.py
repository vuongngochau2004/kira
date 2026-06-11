"""Base entity class for domain models.

Entities are domain objects with a unique identity that persists
across state changes. This base class provides common identity
and equality semantics following Domain-Driven Design principles.

Example:
    >>> from src.shared.kernel.base.entity import Entity
    >>> from uuid import UUID, uuid4
    >>>
    >>> class Document(Entity):
    ...     def __init__(self, filename: str, user_id: str, id: UUID | None = None):
    ...         super().__init__(id=id)
    ...         self.filename = filename
    ...         self.user_id = user_id
"""

from dataclasses import dataclass, field
from uuid import UUID, uuid4
from typing import Any


@dataclass
class Entity:
    """Base class for all domain entities.

    Entities are distinguished by their identity (id), not their attributes.
    Two entities with the same id are considered equal regardless of their
    attribute values.

    Attributes:
        id: Unique identifier for the entity. Auto-generated if not provided.
    """

    id: UUID = field(default_factory=uuid4)

    def __eq__(self, other: Any) -> bool:
        """Two entities are equal if they have the same type and id."""
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on entity id for use in sets and dicts."""
        return hash(self.id)

    def __repr__(self) -> str:
        """String representation showing class name and id."""
        return f"{self.__class__.__name__}(id={self.id})"