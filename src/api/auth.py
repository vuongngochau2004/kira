"""Authentication API endpoints - register, login, refresh, me."""

import sys
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.database import get_session
from src.database.models import User
from src.auth.security import (
    hash_password,
    verify_password,
    create_token_pair,
    decode_token,
)
from src.auth.dependencies import get_current_user
from src.models.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserWithTokenResponse,
)

router = APIRouter()


@router.post("/register", response_model=UserWithTokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegisterRequest,
    db: AsyncSession = Depends(get_session),
):
    """Register a new user account."""
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == data.email).where(User.deleted_at.is_(None))
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    user = User(
        id=uuid.uuid4(),
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role="user",
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create tokens
    tokens = create_token_pair(str(user.id), user.email)

    return UserWithTokenResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )


@router.post("/login", response_model=UserWithTokenResponse)
async def login(
    data: UserLoginRequest,
    db: AsyncSession = Depends(get_session),
):
    """Login with email and password."""
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == data.email).where(User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create tokens
    tokens = create_token_pair(str(user.id), user.email)

    return UserWithTokenResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_session),
):
    """Refresh access token using refresh token."""
    try:
        payload = decode_token(refresh_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {e}",
        )

    # Check token type
    token_type = payload.get("type")
    if token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # Get user
    user_id = payload.get("sub")
    result = await db.execute(
        select(User).where(User.id == user_id).where(User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new token pair
    tokens = create_token_pair(str(user.id), user.email)

    return TokenResponse(**tokens)


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user information."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
    }
