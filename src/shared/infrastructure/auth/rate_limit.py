"""Redis-backed request limits for expensive and authentication endpoints."""

import hashlib
import time
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from loguru import logger
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.config.config import settings
from src.shared.infrastructure.auth.dependencies import get_current_user
from src.shared.infrastructure.persistence.database.models import User

_INCREMENT_WITH_EXPIRY = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


async def _check_limit(scope: str, identity: str, maximum: int, window_seconds: int) -> None:
    """Apply an atomic, fixed-window Redis counter for one identity."""
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    window = int(time.time()) // window_seconds
    key = f"kira:rate:{scope}:{digest}:{window}"
    client = Redis.from_url(
        settings.celery_broker_url,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    try:
        count = int(await client.eval(_INCREMENT_WITH_EXPIRY, 1, key, window_seconds + 1))
    except RedisError as exc:
        logger.exception("Rate limit storage unavailable for {}", scope)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Request limit service unavailable",
        ) from exc
    finally:
        await client.aclose()

    if count > maximum:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": str(window_seconds)},
        )


def limit_ip_requests(scope: str, maximum: int, window_seconds: int) -> Callable:
    """Create a request limit dependency keyed by the connected client IP."""

    async def dependency(request: Request) -> None:
        address = request.client.host if request.client else "unknown"
        await _check_limit(scope, f"ip:{address}", maximum, window_seconds)

    return dependency


def limit_user_requests(scope: str, maximum: int, window_seconds: int) -> Callable:
    """Create a request limit dependency keyed by authenticated user ID."""

    async def dependency(current_user: User = Depends(get_current_user)) -> None:
        await _check_limit(scope, f"user:{current_user.id}", maximum, window_seconds)

    return dependency
