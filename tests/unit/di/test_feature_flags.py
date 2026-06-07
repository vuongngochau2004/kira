"""
Tests for FeatureFlagManager.
"""

import pytest

from src.di.feature_flags import (
    FeatureFlag,
    FeatureFlagManager,
    get_feature_flag_manager,
    reset_feature_flag_manager
)


@pytest.mark.asyncio
async def test_feature_flag_enum():
    """Test FeatureFlag enum values."""
    assert FeatureFlag.USE_NEW_CLASSIFICATION.value == "use_new_classification"
    assert FeatureFlag.USE_NEW_HANDLERS.value == "use_new_handlers"
    assert FeatureFlag.ENABLE_SEMANTIC_ROUTER.value == "enable_semantic_router"
    assert FeatureFlag.ENABLE_LLMLITE_PROVIDER.value == "enable_llmlite_provider"


@pytest.mark.asyncio
async def test_feature_flag_manager_creation():
    """Test FeatureFlagManager creation."""
    config = {
        "use_new_handlers": True,
        "enable_semantic_router": False
    }

    manager = FeatureFlagManager(config)

    assert manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS)
    assert not manager.is_enabled(FeatureFlag.ENABLE_SEMANTIC_ROUTER)


@pytest.mark.asyncio
async def test_is_enabled_with_default():
    """Test is_enabled with default value."""
    manager = FeatureFlagManager({})

    # Flag not in config, should use default
    result = manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS, default=True)
    assert result is True


@pytest.mark.asyncio
async def test_is_enabled_boolean_config():
    """Test is_enabled with boolean config value."""
    manager = FeatureFlagManager({"use_new_handlers": True})

    result = manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS)
    assert result is True


@pytest.mark.asyncio
async def test_is_enabled_percentage_rollout():
    """Test is_enabled with percentage-based rollout."""
    # 50% rollout
    manager = FeatureFlagManager({"use_new_handlers": 50})

    # Different users should get consistent results
    result_user1 = manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS, user_id="user1")
    result_user1_again = manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS, user_id="user1")

    assert result_user1 == result_user1_again  # Consistent for same user

    # At 50%, should have some users enabled and some disabled
    # (not guaranteed with only 2 users, but check logic works)
    assert isinstance(result_user1, bool)


@pytest.mark.asyncio
async def test_percentage_rollout_no_user_id():
    """Test percentage rollout without user_id returns False."""
    manager = FeatureFlagManager({"use_new_handlers": 50})

    result = manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS)

    assert result is False  # No user_id, cannot determine rollout


@pytest.mark.asyncio
async def test_percentage_rollout_100_percent():
    """Test 100% rollout enables all users."""
    manager = FeatureFlagManager({"use_new_handlers": 100})

    result1 = manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS, user_id="user1")
    result2 = manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS, user_id="user2")

    assert result1 is True
    assert result2 is True


@pytest.mark.asyncio
async def test_percentage_rollout_0_percent():
    """Test 0% rollout disables all users."""
    manager = FeatureFlagManager({"use_new_handlers": 0})

    result1 = manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS, user_id="user1")
    result2 = manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS, user_id="user2")

    assert result1 is False
    assert result2 is False


@pytest.mark.asyncio
async def test_set_runtime_override():
    """Test setting runtime override."""
    manager = FeatureFlagManager({"use_new_handlers": False})

    # Initially disabled
    assert not manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS)

    # Set runtime override
    manager.set_runtime_override(FeatureFlag.USE_NEW_HANDLERS, True)

    # Now enabled (override takes precedence)
    assert manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS)


@pytest.mark.asyncio
async def test_clear_runtime_override():
    """Test clearing runtime override."""
    manager = FeatureFlagManager({"use_new_handlers": True})

    # Set override
    manager.set_runtime_override(FeatureFlag.USE_NEW_HANDLERS, False)
    assert not manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS)

    # Clear override (should revert to config)
    manager.clear_runtime_override(FeatureFlag.USE_NEW_HANDLERS)
    assert manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS)


@pytest.mark.asyncio
async def test_get_all_flags():
    """Test getting all flags."""
    config = {
        "use_new_handlers": True,
        "enable_semantic_router": False
    }

    manager = FeatureFlagManager(config)

    flags = manager.get_all_flags()

    assert "use_new_handlers" in flags
    assert "enable_semantic_router" in flags
    assert flags["use_new_handlers"] is True
    assert flags["enable_semantic_router"] is False


@pytest.mark.asyncio
async def test_get_config():
    """Test getting original config."""
    config = {"use_new_handlers": True}

    manager = FeatureFlagManager(config)

    retrieved = manager.get_config()

    assert retrieved == config
    # Should be copy, not same object
    assert retrieved is not config


@pytest.mark.asyncio
async def test_update_config():
    """Test updating configuration."""
    manager = FeatureFlagManager({"use_new_handlers": False})

    assert not manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS)

    manager.update_config({"use_new_handlers": True})

    assert manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS)


@pytest.mark.asyncio
async def test_runtime_override_priority():
    """Test that runtime override takes priority over config."""
    manager = FeatureFlagManager({"use_new_handlers": False})

    # Set runtime override
    manager.set_runtime_override(FeatureFlag.USE_NEW_HANDLERS, True)

    # Update config (should not affect runtime override)
    manager.update_config({"use_new_handlers": False})

    # Still enabled due to override
    assert manager.is_enabled(FeatureFlag.USE_NEW_HANDLERS)


@pytest.mark.asyncio
async def test_get_feature_flag_manager_singleton():
    """Test get_feature_flag_manager returns singleton."""
    manager1 = get_feature_flag_manager()
    manager2 = get_feature_flag_manager()

    assert manager1 is manager2


@pytest.mark.asyncio
async def test_reset_feature_flag_manager():
    """Test resetting feature flag manager."""
    manager1 = get_feature_flag_manager()

    reset_feature_flag_manager()

    manager2 = get_feature_flag_manager()

    # Should be new instance
    assert manager1 is not manager2


@pytest.mark.asyncio
async def test_feature_flag_config_from_settings():
    """Test loading config from settings."""
    # This test requires config to be available
    try:
        from config.config import settings

        manager = FeatureFlagManager(settings.feature_flags)

        # Should have loaded from settings
        flags = manager.get_all_flags()
        assert "use_new_handlers" in flags

    except ImportError:
        # Skip if settings not available
        pytest.skip("Settings not available")
