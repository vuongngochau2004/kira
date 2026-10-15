"""Authentication request and response schemas."""

from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=255)


class UserLoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response after login/register."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class UserResponse(BaseModel):
    """User response."""

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class UserWithTokenResponse(UserResponse):
    """User response with tokens."""

    access_token: str
    refresh_token: str


__all__ = [
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "TokenRefreshRequest",
    "UserResponse",
    "UserWithTokenResponse",
]
