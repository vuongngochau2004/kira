"""Authentication module exports.

Provides JWT token management, password hashing, CSRF protection,
and FastAPI route dependencies for authentication.
"""

from src.shared.infrastructure.auth.dependencies import (
    get_current_active_user,
    get_current_user,
    optional_auth_dependency,
    require_auth,
)
from src.shared.infrastructure.auth.jwt_cookie import (
    clear_auth_cookies,
    set_auth_cookies,
)
from src.shared.infrastructure.auth.security import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "create_token_pair",
    "get_current_user",
    "get_current_active_user",
    "require_auth",
    "optional_auth_dependency",
    "set_auth_cookies",
    "clear_auth_cookies",
]
