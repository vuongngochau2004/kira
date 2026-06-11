"""DEPRECATED: Use src.shared.infrastructure.auth.jwt_cookie instead."""

from src.shared.infrastructure.auth.jwt_cookie import (
    set_auth_cookies,
    clear_auth_cookies,
)

__all__ = [
    "set_auth_cookies",
    "clear_auth_cookies",
]
