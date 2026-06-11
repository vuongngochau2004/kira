"""Shared domain value objects.

Value objects are immutable objects that represent descriptive
aspects of the domain with no conceptual identity of their own.
They are defined by their attributes rather than a unique ID.
"""

from src.shared.domain.value_objects.citation import Citation

__all__ = [
    "Citation",
]