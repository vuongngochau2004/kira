"""Base classes for the shared kernel.

Provides abstract base classes for use cases, repositories, and entities
that all modules can depend on. These follow DIP (Dependency Inversion Principle)
by defining contracts that concrete implementations must fulfill.
"""

from src.shared.kernel.base.use_case import UseCase
from src.shared.kernel.base.repository import Repository
from src.shared.kernel.base.entity import Entity

__all__ = [
    "UseCase",
    "Repository",
    "Entity",
]