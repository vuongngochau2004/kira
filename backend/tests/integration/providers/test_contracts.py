"""Opt-in contracts against the local Docker development stack."""

import os

import pytest

from kira.providers.embedding.api import EmbeddingAPIAdapter
from kira.providers.storage import MinioStorage
from kira.providers.vector_store import QdrantVectorStore

pytestmark = pytest.mark.integration


def _integration_enabled() -> bool:
    return os.getenv("RUN_INTEGRATION") == "1"


@pytest.mark.asyncio
async def test_external_adapter_health_contracts():
    if not _integration_enabled():
        pytest.skip("Set RUN_INTEGRATION=1 with Docker services running")

    assert await QdrantVectorStore().health_check()
    # MinioStorage has no health endpoint; bucket initialization is exercised by upload tests.
    assert MinioStorage() is not None


@pytest.mark.asyncio
async def test_embedding_adapter_health_contract():
    """Run only when a separately deployed embedding API is available."""
    if os.getenv("RUN_EMBEDDING_INTEGRATION") != "1":
        pytest.skip("Set RUN_EMBEDDING_INTEGRATION=1 with an embedding API running")

    assert await EmbeddingAPIAdapter().health_check()
