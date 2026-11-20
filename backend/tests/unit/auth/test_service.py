"""Tests for kira.auth.service."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from kira.auth.service import IdentityService


class FakeUsers:
    def __init__(self):
        self.users = {}

    async def get_by_email(self, email):
        return self.users.get(email)

    async def get_active_by_id(self, user_id):
        return next(
            (user for user in self.users.values() if str(user.id) == user_id and user.is_active),
            None,
        )

    async def create(self, *, email, hashed_password, full_name):
        user = SimpleNamespace(
            id=uuid4(),
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
        )
        self.users[email] = user
        return user


@pytest.mark.asyncio
async def test_identity_register_authenticate_and_active_lookup():
    service = IdentityService(
        FakeUsers(),
        lambda password: f"hash:{password}",
        lambda raw, hashed: hashed == f"hash:{raw}",
    )
    user = await service.register(email="a@example.com", password="secret", full_name="A")

    assert (await service.authenticate(email="a@example.com", password="secret")).id == user.id
    assert await service.authenticate(email="a@example.com", password="wrong") is None
    assert (await service.get_active_user(str(user.id))).email == "a@example.com"
    with pytest.raises(ValueError, match="already registered"):
        await service.register(email="a@example.com", password="secret", full_name="A")
