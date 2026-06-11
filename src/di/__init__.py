"""Dependency injection package - Backward compatibility shim.

DEPRECATED: This package is deprecated. Use src.shared.kernel.di instead.
All DI components have been moved to src.shared.kernel.di as part of
the modular monolith migration (Phase 1).

This module re-exports all DI components from the new location for backward compatibility.
New code should import directly from src.shared.kernel.di.
"""

from src.shared.kernel.di.container import ServiceContainer
from src.shared.kernel.di.feature_flags import FeatureFlag, FeatureFlagManager
from src.shared.kernel.di.registry import ServiceRegistry, get_container

__all__ = [
    "ServiceContainer",
    "FeatureFlag",
    "FeatureFlagManager",
    "ServiceRegistry",
    "get_container",
]