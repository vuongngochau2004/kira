"""Dependency injection package for K.I.R.A.

This package implements ABC-based dependency injection following the DIP principle.
Moved from src/di/ to src/shared/kernel/di/ as part of modular monolith migration (Phase 1).
"""

from src.shared.kernel.di.container import ServiceContainer
from src.shared.kernel.di.feature_flags import (
    FeatureFlag,
    FeatureFlagManager,
    get_feature_flag_manager,
    reset_feature_flag_manager
)
from src.shared.kernel.di.registry import ServiceRegistry, get_container

__all__ = [
    "ServiceContainer",
    "FeatureFlag",
    "FeatureFlagManager",
    "get_feature_flag_manager",
    "reset_feature_flag_manager",
    "ServiceRegistry",
    "get_container",
]