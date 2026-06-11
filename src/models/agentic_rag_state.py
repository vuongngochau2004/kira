"""DEPRECATED: Use src.modules.rag.domain.state.rag_state instead.

This module is kept for backward compatibility only.
All new code should import from src.modules.rag.domain.state.rag_state.
"""
import warnings

warnings.warn(
    "src.models.agentic_rag_state is deprecated. "
    "Use src.modules.rag.domain.state.rag_state",
    DeprecationWarning,
    stacklevel=2,
)

from src.modules.rag.domain.state.rag_state import *  # noqa
