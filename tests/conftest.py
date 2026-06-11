"""Root conftest.py defining global fixtures."""

import pytest
import asyncio
import uuid
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from src.server.main import app
from src.shared.infrastructure.auth.dependencies import get_current_user
from src.shared.infrastructure.persistence.database.models import User, UserRole

@pytest.fixture
def mock_user() -> User:
    """Mock user for API authentication."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        role=UserRole.USER.value,
        is_active=True,
    )

@pytest.fixture
async def authenticated_client(mock_user: User) -> AsyncGenerator[AsyncClient, None]:
    """Test client authenticated with mock user."""
    from src.shared.infrastructure.persistence.database.session import async_session_factory
    from sqlalchemy import select

    # Persist mock user to database to prevent Foreign Key constraints failing on child tables (like conversations)
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.email == mock_user.email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            # Reuse the existing user's ID to avoid UniqueViolation on email
            mock_user.id = existing_user.id
        else:
            await session.merge(mock_user)
            await session.commit()

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as client:
        yield client

    app.dependency_overrides.clear()
