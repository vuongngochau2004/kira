"""Shared domain module.

Contains domain entities and value objects that are shared
across all modules in the modular monolith. Domain objects here
represent pure business concepts independent of infrastructure concerns.
"""

from src.shared.domain.entities.document import DocumentEntity
from src.shared.domain.entities.conversation import ConversationEntity
from src.shared.domain.entities.user import UserEntity
from src.shared.domain.value_objects.citation import Citation

__all__ = [
    # Entities
    "DocumentEntity",
    "ConversationEntity",
    "UserEntity",
    # Value Objects
    "Citation",
]