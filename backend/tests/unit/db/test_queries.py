"""Soft-delete helpers must write naive UTC timestamps (columns are TIMESTAMP WITHOUT TIME ZONE).

An aware datetime made asyncpg reject DELETE /api/v1/chat/conversations/{id} with HTTP 500.
"""

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from kira.db.queries import (
    soft_delete_conversation,
    soft_delete_document,
)


def _session_returning(row: object) -> AsyncMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    session = AsyncMock()
    session.execute.return_value = result
    return session


@pytest.mark.asyncio
@pytest.mark.parametrize("soft_delete", [soft_delete_conversation, soft_delete_document])
async def test_soft_delete_sets_naive_utc_deleted_at(soft_delete):
    row = SimpleNamespace(deleted_at=None)
    session = _session_returning(row)

    assert await soft_delete(uuid.uuid4(), session) is True

    assert row.deleted_at is not None
    assert row.deleted_at.tzinfo is None
    assert abs(row.deleted_at - datetime.now(UTC).replace(tzinfo=None)) < timedelta(seconds=5)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("soft_delete", [soft_delete_conversation, soft_delete_document])
async def test_soft_delete_returns_false_when_missing(soft_delete):
    session = _session_returning(None)

    assert await soft_delete(uuid.uuid4(), session) is False
    session.commit.assert_not_awaited()
