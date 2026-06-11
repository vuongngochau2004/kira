"""JWT cookie utilities for httpOnly cookie authentication."""

from datetime import timedelta

from fastapi import Response
from src.config.config import settings


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Set httpOnly cookies for JWT tokens."""
    is_secure = not settings.debug
    samesite_mode = "lax" if settings.debug else "strict"

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_secure,
        samesite=samesite_mode,
        max_age=int(timedelta(minutes=settings.jwt_access_token_expire_minutes).total_seconds())
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_secure,
        samesite=samesite_mode,
        max_age=int(timedelta(days=settings.jwt_refresh_token_expire_days).total_seconds())
    )


def clear_auth_cookies(response: Response):
    """Clear auth cookies."""
    is_secure = not settings.debug
    samesite_mode = "lax" if settings.debug else "strict"

    response.set_cookie(
        key="access_token",
        value="",
        max_age=0,
        httponly=True,
        secure=is_secure,
        samesite=samesite_mode
    )

    response.set_cookie(
        key="refresh_token",
        value="",
        max_age=0,
        httponly=True,
        secure=is_secure,
        samesite=samesite_mode
    )