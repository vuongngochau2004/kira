"""
Dependency injection package for K.I.R.A.

This package implements protocol-based dependency injection following the DIP principle.
"""

from src.di.container import ServiceContainer
from src.di.feature_flags import FeatureFlag, FeatureFlagManager
from src.di.registry import ServiceRegistry, get_container

__all__ = [
    "ServiceContainer",
    "FeatureFlag",
    "FeatureFlagManager",
    "ServiceRegistry",
    "get_container",
]
