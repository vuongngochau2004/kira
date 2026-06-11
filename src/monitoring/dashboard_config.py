"""DEPRECATED: Use src.shared.infrastructure.monitoring.dashboard_config instead."""

from src.shared.infrastructure.monitoring.dashboard_config import (
    DashboardConfig,
    MetricDefinition,
    AlertRule,
    MetricType,
    AlertSeverity,
    get_dashboard_config,
)

__all__ = [
    "DashboardConfig",
    "MetricDefinition",
    "AlertRule",
    "MetricType",
    "AlertSeverity",
    "get_dashboard_config",
]
