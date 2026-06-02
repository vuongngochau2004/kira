"""CSRF protection utilities for httpOnly cookie authentication.

NOTE: CSRF protection is partially implemented via SameSite=strict cookie attribute
in production mode (see src/auth/jwt_cookie.py). This provides baseline protection
against CSRF attacks for most scenarios.

For production environments with higher security requirements, implement token-based
CSRF protection:

1. Generate CSRF token per session:
   - Store in httpOnly cookie (csrf_token)
   - Return in /me endpoint response (csrf_token header)

2. Validate CSRF token on state-changing operations:
   - Decorate POST/PUT/DELETE endpoints with @csrf_protect
   - Compare request header vs cookie value

3. Frontend integration:
   - Fetch CSRF token from /me endpoint
   - Include in X-CSRF-Token header for state-changing requests

Current Status: SameSite=strict provides protection. Full token-based CSRF
protection is planned for future implementation.
"""

import secrets
import hashlib
from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# CSRF token length (bytes)
CSRF_TOKEN_LENGTH = 32


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token.

    Returns:
        Hex-encoded CSRF token
    """
    return secrets.token_hex(CSRF_TOKEN_LENGTH)


def validate_csrf_token(token: str, expected_token: str) -> bool:
    """Validate CSRF token using constant-time comparison.

    Args:
        token: Token from request header
        expected_token: Expected token from session/cookie

    Returns:
        True if tokens match, False otherwise
    """
    if not token or not expected_token:
        return False

    # Constant-time comparison to prevent timing attacks
    return secrets.compare_digest(token, expected_token)


async def get_csrf_token_from_cookie(request: Request) -> str | None:
    """Get CSRF token from httpOnly cookie.

    Args:
        request: FastAPI Request object

    Returns:
        CSRF token string or None
    """
    return request.cookies.get("csrf_token")


async def get_csrf_token_from_header(request: Request) -> str | None:
    """Get CSRF token from request header.

    Args:
        request: FastAPI Request object

    Returns:
        CSRF token string or None
    """
    return request.headers.get("X-CSRF-Token")


def csrf_protect_decorator(async_handler):
    """Decorator to protect endpoints from CSRF attacks.

    Usage:
        @router.post("/change-password")
        @csrf_protect_decorator
        async def change_password(...):
            ...

    NOTE: This decorator is a placeholder for future implementation.
    Current CSRF protection relies on SameSite=strict cookie attribute.
    """
    async def wrapper(*args, **kwargs):
        # Placeholder: CSRF validation would happen here
        # For now, rely on SameSite=strict protection
        return await async_handler(*args, **kwargs)
    return wrapper


# TODO: Implement full CSRF protection when frontend is ready
# 1. Add /csrf-token endpoint to return token
# 2. Set csrf_token cookie on authentication
# 3. Validate on state-changing endpoints
# 4. Update frontend to fetch and include token
