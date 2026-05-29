"""Authentication dependencies for FastAPI routes."""

import sys
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.config import settings
from src.auth.security import decode_token
from src.database import get_session
from src.database.models import User
from sqlalchemy.ext.asyncio import AsyncSession


security = HTTPBearer(auto_error=False)

# Dev user ID used when auth is disabled
_DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _get_or_create_dev_user(db: AsyncSession) -> User:
    """Get or create a development user for auth-disabled mode."""
    from sqlalchemy import select

    result = await db.execute(
        select(User).where(User.id == _DEV_USER_ID)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=_DEV_USER_ID,
            email="dev@kira.local",
            hashed_password="disabled",
            full_name="Dev User",
            role="admin",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: AsyncSession = Depends(get_session),
) -> User:
    """Validate JWT and return current user. Bypassed when AUTH_ENABLED=false."""
    # --- Auth bypass for development ---
    if not settings.auth_enabled:
        return await _get_or_create_dev_user(db)

    # --- Normal JWT auth flow ---
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = credentials.credentials

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


def optional_auth():
    """Optional authentication - doesn't raise if no token provided."""
    async def _optional_auth(
        credentials: HTTPAuthorizationCredentials | None = Depends(
            HTTPBearer(auto_error=False)
        ),
        db: AsyncSession = Depends(get_session),
    ) -> User | None:
        if not credentials:
            return None

        try:
            return await get_current_user(credentials, db)
        except HTTPException:
            return None

    return _optional_auth


# Create the actual optional dependency
optional_auth_dependency = optional_auth()
