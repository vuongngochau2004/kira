"""Security utilities - password hashing and JWT token management."""

import sys
from pathlib import Path
import uuid
from datetime import datetime, timedelta, timezone

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from config.config import settings


# ===== Password Hashing =====

import bcrypt


def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against its hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# ===== JWT Token Service =====


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token with enhanced security claims."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    claims = {
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "exp": expire,
    }
    if "type" not in to_encode:
        claims["type"] = "access"

    to_encode.update(claims)
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        headers={"typ": "JWT", "alg": settings.jwt_algorithm},
    )


def create_refresh_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT refresh token with enhanced security claims."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(days=settings.jwt_refresh_token_expire_days)
    )
    claims = {
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "exp": expire,
    }
    if "type" not in to_encode:
        claims["type"] = "refresh"

    to_encode.update(claims)
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        headers={"typ": "JWT", "alg": settings.jwt_algorithm},
    )


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token with audience check."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
        )
        return payload
    except ExpiredSignatureError:
        raise JWTError("Token has expired") from None
    except JWTError as e:
        raise JWTError(f"Invalid token: {e}") from None


def create_token_pair(user_id: str, email: str) -> dict:
    """Create both access and refresh tokens for a user."""
    token_data = {"sub": user_id, "email": email}
    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "token_type": "bearer",
    }
