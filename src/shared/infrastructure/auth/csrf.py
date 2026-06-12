"""CSRF protection utilities for httpOnly cookie authentication.

NOTE: CSRF protection is partially implemented via SameSite=strict cookie attribute
in production mode (see jwt_cookie.py). This provides baseline protection
against CSRF attacks for most scenarios.

For production environments with higher security requirements, implement token-based
CSRF protection.

Current Status: SameSite=strict provides protection. Full token-based CSRF
protection is planned for future implementation.
"""

import secrets
from fastapi import Request


# CSRF token length (bytes)
CSRF_TOKEN_LENGTH = 32


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_hex(CSRF_TOKEN_LENGTH)


def validate_csrf_token(token: str, expected_token: str) -> bool:
    """Validate CSRF token using constant-time comparison."""
    if not token or not expected_token:
        return False

    # Constant-time comparison to prevent timing attacks
    return secrets.compare_digest(token, expected_token)


async def get_csrf_token_from_cookie(request: Request) -> str | None:
    """Get CSRF token from httpOnly cookie."""
    return request.cookies.get("csrf_token")


async def get_csrf_token_from_header(request: Request) -> str | None:
    """Get CSRF token from request header."""
    return request.headers.get("X-CSRF-Token")


def csrf_protect_decorator(async_handler):
    """Decorator to protect endpoints from CSRF attacks.

    NOTE: This decorator is a placeholder for future implementation.
    Current CSRF protection relies on SameSite=strict cookie attribute.
    """
    async def wrapper(*args, **kwargs):
        return await async_handler(*args, **kwargs)
    return wrapper


# TODO: Implement full CSRF protection when frontend is ready