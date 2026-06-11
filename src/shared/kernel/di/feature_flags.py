"""
Feature flag management for gradual rollout.

Environment-based and runtime feature flag management with percentage-based rollout.
"""

import hashlib
from enum import Enum
from functools import lru_cache
from typing import Optional, Any


class FeatureFlag(str, Enum):
    """
    Feature flags for gradual rollout.

    Each flag represents a feature that can be toggled independently.

    Flags:
        - USE_NEW_CLASSIFICATION: Enable new classification strategies (Phase 02)
        - USE_NEW_HANDLERS: Enable new handler architecture (Phase 03)
        - ENABLE_SEMANTIC_ROUTER: Enable semantic routing (future)
        - ENABLE_LLMLITE_PROVIDER: Enable LLMlite provider (experimental)
    """

    USE_NEW_CLASSIFICATION = "use_new_classification"
    USE_NEW_HANDLERS = "use_new_handlers"
    ENABLE_SEMANTIC_ROUTER = "enable_semantic_router"
    ENABLE_LLMLITE_PROVIDER = "enable_llmlite_provider"


class FeatureFlagManager:
    """
    Feature flag management with runtime toggles and percentage-based rollout.

    Supports:
    - Environment-based configuration (from settings)
    - Runtime overrides (instant toggle without restart)
    - Percentage-based rollout (gradual rollout by user_id hash)
    - Consistent user assignment (hash-based, no drift)

    Example:
        >>> manager = FeatureFlagManager({"use_new_handlers": True})
        >>> manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS, user_id="user123")
        True
        >>> manager.set_runtime_override(FeatureFlag.USE_NEW_HANDLERS, False)
        >>> manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS, user_id="user123")
        False
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize feature flag manager.

        Args:
            config: Feature flag configuration (typically from settings)
        """
        self._config = config.copy() if config else {}
        self._runtime_overrides: dict[str, bool] = {}

    def is_enabled(
        self,
        flag: FeatureFlag,
        user_id: Optional[str] = None,
        default: bool = False
    ) -> bool:
        """
        Check if feature flag is enabled.

        Priority:
        1. Runtime override (instant toggle)
        2. Configuration value
        3. Percentage-based rollout (if value is int)
        4. Default value

        Args:
            flag: Feature flag enum
            user_id: User ID for percentage-based rollout
            default: Default value if flag not configured

        Returns:
            True if feature is enabled for the user

        Example:
            >>> # Boolean config
            >>> manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS)
            True
            >>>
            >>> # Percentage-based rollout (50% of users)
            >>> manager.is_enabled(
            ...     FeatureFlag.USE_NEW_HANDLERS,
            ...     user_id="user123"
            ... )
            True  # or False based on user_id hash
        """
        # Runtime override takes precedence
        if flag.value in self._runtime_overrides:
            return self._runtime_overrides[flag.value]

        # Config value
        enabled = self._config.get(flag.value, default)

        # Boolean config (check before int since bool is subclass of int)
        if isinstance(enabled, bool):
            return enabled

        # Percentage rollout (if value is int but not bool)
        if isinstance(enabled, int) and not isinstance(enabled, bool):
            if user_id:
                # Hash user_id for consistent assignment
                user_hash = int(hashlib.sha256(user_id.encode()).hexdigest(), 16) % 100
                return user_hash < enabled
            return False

        # Fallback for other types
        return bool(enabled)

    def set_runtime_override(self, flag: FeatureFlag, enabled: bool) -> None:
        """
        Set runtime override (instant toggle without restart).

        Args:
            flag: Feature flag enum
            enabled: Whether to enable the feature

        Example:
            >>> # Instantly disable new handlers
            >>> manager.set_runtime_override(FeatureFlag.USE_NEW_HANDLERS, False)
        """
        self._runtime_overrides[flag.value] = enabled

    def clear_runtime_override(self, flag: FeatureFlag) -> None:
        """
        Clear runtime override (revert to config value).

        Args:
            flag: Feature flag enum

        Example:
            >>> manager.clear_runtime_override(FeatureFlag.USE_NEW_HANDLERS)
        """
        self._runtime_overrides.pop(flag.value, None)

    def get_all_flags(self) -> dict[str, Any]:
        """
        Get all feature flags with current state.

        Returns:
            Dict with flag names and their effective state

        Example:
            >>> flags = manager.get_all_flags()
            >>> print(flags["use_new_handlers"])
            True
        """
        result = {}

        for flag in FeatureFlag:
            # Get effective value (with override)
            if flag.value in self._runtime_overrides:
                result[flag.value] = self._runtime_overrides[flag.value]
            else:
                result[flag.value] = self._config.get(flag.value, False)

        return result

    def get_config(self) -> dict[str, Any]:
        """
        Get original configuration (without runtime overrides).

        Returns:
            Original config dict

        Example:
            >>> config = manager.get_config()
        """
        return self._config.copy()

    def update_config(self, config: dict[str, Any]) -> None:
        """
        Update configuration (does not clear runtime overrides).

        Args:
            config: New configuration values

        Example:
            >>> manager.update_config({"use_new_handlers": False})
        """
        self._config.update(config)


@lru_cache(maxsize=1)
def get_feature_flag_manager() -> FeatureFlagManager:
    """
    Get singleton feature flag manager.

    Loads configuration from settings and caches the manager instance.

    Returns:
        FeatureFlagManager singleton

    Example:
        >>> manager = get_feature_flag_manager()
        >>> is_enabled = manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS)
    """
    try:
        from src.config.config import settings
        config = getattr(settings, "feature_flags", {})
    except Exception:
        # Fallback if settings not available
        config = {}

    return FeatureFlagManager(config)


def reset_feature_flag_manager() -> None:
    """
    Reset the singleton feature flag manager.

    Clears the cached manager instance. Useful for testing.

    Example:
        >>> reset_feature_flag_manager()
        >>> manager = get_feature_flag_manager()  # Fresh instance
    """
    get_feature_flag_manager.cache_clear()
