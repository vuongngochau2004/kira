"""Authentication dependencies for FastAPI routes."""

from typing import Annotated

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.shared.infrastructure.auth.security import decode_token
from src.shared.infrastructure.persistence.database import get_session
from src.shared.infrastructure.persistence.database.models import User, UserRole
from sqlalchemy.ext.asyncio import AsyncSession


security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    db: AsyncSession = Depends(get_session),
) -> User:
    """Validate JWT and return current user from httpOnly cookie or Authorization header.

    Token Priority (Cookie-First Strategy):
    1. httpOnly cookie (access_token) - PRIMARY, most secure
    2. Authorization header (Bearer token) - FALLBACK, backward compatibility
    """
    # Priority: httpOnly cookie > Authorization header
    token = request.cookies.get("access_token")

    # Fallback to Authorization header for backward compatibility
    if not token and credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = decode_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identifier",
        )

    # Check token type
    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # Get user from database
    from sqlalchemy import select

    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .where(User.deleted_at.is_(None))
        .where(User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user



async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Check if current user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return current_user


async def require_auth(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Require authenticated user (alias for get_current_active_user)."""
    return current_user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Require an active administrator account."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def optional_auth():
    """Optional authentication - doesn't raise if no token provided."""
    async def _optional_auth(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(
            HTTPBearer(auto_error=False)
        ),
        db: AsyncSession = Depends(get_session),
    ) -> User | None:
        if not credentials and not request.cookies.get("access_token"):
            return None

        try:
            return await get_current_user(request, credentials, db)
        except HTTPException:
            return None

    return _optional_auth


# Create the actual optional dependency
optional_auth_dependency = optional_auth()
