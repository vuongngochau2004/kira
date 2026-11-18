"""process_document must store a readable error even when the exception text is empty."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.constants import DocumentStatus
from src.modules.document.domain.services import pipeline


@pytest.mark.asyncio
async def test_failed_status_keeps_exception_type_when_message_is_empty():
    repository = AsyncMock()

    with patch.object(pipeline, "_process_sync", side_effect=httpx.ReadTimeout("")):
        result = await pipeline.process_document(
            document_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            storage_path="docs/file.pdf",
            storage=AsyncMock(),
            embedding=MagicMock(),
            vector_store=MagicMock(),
            ocr=MagicMock(),
            repository=repository,
        )

    assert result == {"success": False, "error": "Processing failed: ReadTimeout"}
    repository.update_document_status.assert_awaited_once()
    kwargs = repository.update_document_status.await_args.kwargs
    assert kwargs["status"] == DocumentStatus.FAILED.value
    assert kwargs["error_message"] == "Processing failed: ReadTimeout"
