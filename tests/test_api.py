"""Integration tests for K.I.R.A Simplified API."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    """Test client for FastAPI app."""
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def db_session():
    """Database session fixture."""
    from src.database.session import async_session_factory

    async with async_session_factory() as session:
        yield session


class TestHealth:
    """Health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_readiness_check(self, client):
        """Test readiness check endpoint."""
        response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_liveness_check(self, client):
        """Test liveness check endpoint."""
        response = await client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestAuth:
    """Authentication endpoints."""

    @pytest.mark.asyncio
    async def test_register(self, client):
        """Test user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_login(self, client):
        """Test user login."""
        # First register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com",
                "password": "testpassword123",
                "full_name": "Login User",
            },
        )

        # Then login
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login@example.com",
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_me_unauthorized(self, client):
        """Test getting current user without auth."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestDocuments:
    """Document endpoints."""

    @pytest.mark.asyncio
    async def test_upload_document_unauthorized(self, client):
        """Test document upload without authentication."""
        response = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", b"test content", "text/plain")},
        )
        assert response.status_code == 401


class TestChat:
    """Chat endpoints."""

    @pytest.mark.asyncio
    async def test_chat_completions_unauthorized(self, client):
        """Test chat completion without authentication."""
        response = await client.post(
            "/api/v1/chat/completions",
            json={"message": "Hello"},
        )
        assert response.status_code == 401
