"""A document reprocessed successfully must not keep the previous run's error_message."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from kira.documents.repository import (
    update_document_status,
)


async def _update_params(**kwargs) -> dict:
    session = AsyncMock()
    session.execute.return_value = MagicMock()
    await update_document_status(document_id=uuid.uuid4(), db=session, **kwargs)
    statement = session.execute.await_args.args[0]
    return statement.compile().params


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["completed", "processing"])
async def test_non_failed_status_clears_error_message(status: str) -> None:
    params = await _update_params(status=status, chunk_count=19)

    assert "error_message" in params
    assert params["error_message"] is None


@pytest.mark.asyncio
async def test_failed_status_stores_error_message() -> None:
    params = await _update_params(status="failed", error_message="Processing failed: ReadTimeout")

    assert params["error_message"] == "Processing failed: ReadTimeout"


@pytest.mark.asyncio
async def test_failed_status_without_message_keeps_existing_error() -> None:
    params = await _update_params(status="failed")

    assert "error_message" not in params
