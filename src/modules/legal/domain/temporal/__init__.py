"""Temporal resolution of legal questions."""

from src.modules.legal.domain.temporal.rules import (
    TemporalQuery,
    default_temporal_query,
    resolve_temporal_rules,
)

__all__ = ["TemporalQuery", "default_temporal_query", "resolve_temporal_rules"]
