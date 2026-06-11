"""
Feature Flag Integration for Agentic RAG

This module provides feature flag support for gradually rolling out
the Agentic RAG system using percentage-based rollout.
"""

import logging
from typing import Optional
from uuid import UUID

from src.shared.kernel.di.feature_flags import FeatureFlagManager
from models.agentic_rag_state import AgenticRAGConfig

logger = logging.getLogger(__name__)


class AgenticRAGFeatureFlags:
    """
    Feature flags for Agentic RAG rollout.

    Supports:
    - Percentage-based user rollout
    - Per-feature enablement
    - A/B testing integration
    - Gradual rollout strategy
    """

    # Feature flag keys
    FLAG_AGENTIC_RAG_ENABLED = "agentic_rag_enabled"
    FLAG_QUERY_REFINER = "agentic_rag_query_refiner"
    FLAG_RERANKING = "agentic_rag_reranking"
    FLAG_CRITIQUE = "agentic_rag_critique"
    FLAG_VERIFICATION = "agentic_rag_verification"

    def __init__(self, feature_flag_manager: FeatureFlagManager):
        """
        Initialize feature flags.

        Args:
            feature_flag_manager: Feature flag manager instance
        """
        self.ff_manager = feature_flag_manager
        self._setup_flags()

    def _setup_flags(self):
        """Setup default feature flags"""
        # Main Agentic RAG flag - starts at 0% (disabled)
        self.ff_manager.define_flag(
            name=self.FLAG_AGENTIC_RAG_ENABLED,
            percentage=0,  # Start disabled
            description="Enable Agentic RAG pipeline (vs simple RAG)"
        )

        # Individual feature flags
        self.ff_manager.define_flag(
            name=self.FLAG_QUERY_REFINER,
            percentage=50,  # 50% rollout
            description="Enable query refinement agent"
        )

        self.ff_manager.define_flag(
            name=self.FLAG_RERANKING,
            percentage=50,  # 50% rollout
            description="Enable document reranking agent"
        )

        self.ff_manager.define_flag(
            name=self.FLAG_CRITIQUE,
            percentage=30,  # 30% rollout (conservative)
            description="Enable response critique agent"
        )

        self.ff_manager.define_flag(
            name=self.FLAG_VERIFICATION,
            percentage=30,  # 30% rollout (conservative)
            description="Enable final verification agent"
        )

    def is_agentic_rag_enabled(self, user_id: str | UUID) -> bool:
        """
        Check if Agentic RAG is enabled for a user.

        Args:
            user_id: User ID

        Returns:
            True if enabled for this user
        """
        return self.ff_manager.is_enabled_for_user(
            flag_name=self.FLAG_AGENTIC_RAG_ENABLED,
            user_id=str(user_id)
        )

    def get_config_for_user(self, user_id: str | UUID) -> AgenticRAGConfig:
        """
        Get Agentic RAG configuration for a specific user.

        Args:
            user_id: User ID

        Returns:
            AgenticRAGConfig with features enabled/disabled based on flags
        """
        config = AgenticRAGConfig()

        # Main flag
        if not self.is_agentic_rag_enabled(user_id):
            # Agentic RAG disabled, return empty config
            # Caller should fall back to simple RAG
            return config

        # Individual feature flags
        config.enable_query_refinement = self.ff_manager.is_enabled_for_user(
            flag_name=self.FLAG_QUERY_REFINER,
            user_id=str(user_id)
        )

        config.enable_reranking = self.ff_manager.is_enabled_for_user(
            flag_name=self.FLAG_RERANKING,
            user_id=str(user_id)
        )

        config.enable_critique = self.ff_manager.is_enabled_for_user(
            flag_name=self.FLAG_CRITIQUE,
            user_id=str(user_id)
        )

        config.enable_verification = self.ff_manager.is_enabled_for_user(
            flag_name=self.FLAG_VERIFICATION,
            user_id=str(user_id)
        )

        return config

    def set_rollout_percentage(self, flag_name: str, percentage: int):
        """
        Set rollout percentage for a feature flag.

        Args:
            flag_name: Name of the flag
            percentage: Percentage (0-100)
        """
        self.ff_manager.set_percentage(flag_name, percentage)
        logger.info(f"Updated flag {flag_name} to {percentage}% rollout")

    def get_rollout_status(self) -> dict:
        """
        Get current rollout status.

        Returns:
            Dictionary with rollout percentages
        """
        return {
            "agentic_rag_enabled": self.ff_manager.get_percentage(self.FLAG_AGENTIC_RAG_ENABLED),
            "query_refiner": self.ff_manager.get_percentage(self.FLAG_QUERY_REFINER),
            "reranking": self.ff_manager.get_percentage(self.FLAG_RERANKING),
            "critique": self.ff_manager.get_percentage(self.FLAG_CRITIQUE),
            "verification": self.ff_manager.get_percentage(self.FLAG_VERIFICATION),
        }


# ============================================================================
# Rollout Strategy
# ============================================================================

class AgenticRAGRolloutStrategy:
    """
    Rollout strategy for Agentic RAG.

    Provides a phased rollout approach:
    Phase 1: Internal testing (0%)
    Phase 2: Small beta (5-10%)
    Phase 3: Gradual rollout (10-50%)
    Phase 4: Full rollout (100%)
    """

    def __init__(self, feature_flags: AgenticRAGFeatureFlags):
        """
        Initialize rollout strategy.

        Args:
            feature_flags: Feature flags instance
        """
        self.feature_flags = feature_flags

    def rollout_phase_1(self):
        """Phase 1: Internal testing only (0%)"""
        logger.info("Starting Phase 1: Internal testing (0% rollout)")
        self.feature_flags.set_rollout_percentage(
            AgenticRAGFeatureFlags.FLAG_AGENTIC_RAG_ENABLED,
            0
        )

    def rollout_phase_2(self, percentage: int = 5):
        """Phase 2: Small beta rollout (5-10%)"""
        logger.info(f"Starting Phase 2: Beta rollout ({percentage}% rollout)")
        self.feature_flags.set_rollout_percentage(
            AgenticRAGFeatureFlags.FLAG_AGENTIC_RAG_ENABLED,
            percentage
        )

    def rollout_phase_3(self, percentage: int = 25):
        """Phase 3: Gradual rollout (25-50%)"""
        logger.info(f"Starting Phase 3: Gradual rollout ({percentage}% rollout)")
        self.feature_flags.set_rollout_percentage(
            AgenticRAGFeatureFlags.FLAG_AGENTIC_RAG_ENABLED,
            percentage
        )

    def rollout_phase_4(self):
        """Phase 4: Full rollout (100%)"""
        logger.info("Starting Phase 4: Full rollout (100% rollout)")
        self.feature_flags.set_rollout_percentage(
            AgenticRAGFeatureFlags.FLAG_AGENTIC_RAG_ENABLED,
            100
        )

    def get_current_phase(self) -> str:
        """
        Get current rollout phase.

        Returns:
            Phase name
        """
        percentage = self.feature_flags.get_rollout_status()["agentic_rag_enabled"]

        if percentage == 0:
            return "Phase 1: Internal testing"
        elif percentage < 10:
            return "Phase 2: Beta rollout"
        elif percentage < 100:
            return "Phase 3: Gradual rollout"
        else:
            return "Phase 4: Full rollout"


# ============================================================================
# Factory
# ============================================================================

def create_agentic_rag_feature_flags(
    feature_flag_manager: Optional[FeatureFlagManager] = None
) -> AgenticRAGFeatureFlags:
    """
    Factory function to create AgenticRAGFeatureFlags.

    Args:
        feature_flag_manager: Optional feature flag manager

    Returns:
        Configured AgenticRAGFeatureFlags
    """
    if feature_flag_manager is None:
        from src.shared.kernel.di.feature_flags import FeatureFlagManager
        feature_flag_manager = FeatureFlagManager()

    return AgenticRAGFeatureFlags(feature_flag_manager)


def create_agentic_rag_rollout_strategy(
    feature_flags: Optional[AgenticRAGFeatureFlags] = None
) -> AgenticRAGRolloutStrategy:
    """
    Factory function to create rollout strategy.

    Args:
        feature_flags: Optional feature flags

    Returns:
        Configured rollout strategy
    """
    if feature_flags is None:
        feature_flags = create_agentic_rag_feature_flags()

    return AgenticRAGRolloutStrategy(feature_flags)
