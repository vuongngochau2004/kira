"""Dependency composition for the classification module."""

from src.modules.classification.application import Classification


def classification_use_case() -> Classification:
    """Compose the default classification use case."""
    return Classification()


__all__ = ["classification_use_case"]
