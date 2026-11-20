"""Application service for registration and credential validation."""

from typing import Any, Callable

from kira.auth.repository import SqlAlchemyUserAccountRepository


class IdentityService:
    """Use cases for user registration, login and token refresh validation."""

    def __init__(
        self,
        users: SqlAlchemyUserAccountRepository,
        hash_password: Callable[[str], str],
        verify_password: Callable[[str, str], bool],
    ):
        self.users = users
        self._hash_password = hash_password
        self._verify_password = verify_password

    async def register(self, *, email: str, password: str, full_name: str | None) -> Any:
        if await self.users.get_by_email(email):
            raise ValueError("Email already registered")
        return await self.users.create(
            email=email,
            hashed_password=self._hash_password(password),
            full_name=full_name,
        )

    async def authenticate(self, *, email: str, password: str) -> Any | None:
        user = await self.users.get_by_email(email)
        if not user or not self._verify_password(password, user.hashed_password):
            return None
        return user

    async def get_active_user(self, user_id: str) -> Any | None:
        return await self.users.get_active_by_id(user_id)


__all__ = [
    "IdentityService",
]
