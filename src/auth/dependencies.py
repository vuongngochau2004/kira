"""DEPRECATED: Use src.shared.infrastructure.auth.dependencies instead."""

from src.shared.infrastructure.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    require_auth,
    optional_auth_dependency,
)

__all__ = [
    "get_current_user",
    "get_current_active_user",
    "require_auth",
    "optional_auth_dependency",
]
