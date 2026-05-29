"""Embedding service implementation via API."""

import sys
from pathlib import Path
from typing import Any

import httpx

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.config import settings


# HTTP client for embedding API
_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    """Get or create HTTP client for embedding API."""
    global _client
    if _client is None:
        _client = httpx.Client(timeout=30.0)
    return _client


def embed(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts via API.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    client = _get_client()
    base_url = settings.embedding_base_url.rstrip("/")

    # Batch requests to avoid overload
    batch_size = 32
    if len(texts) > batch_size:
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            results.extend(_embed_batch(client, base_url, batch))
        return results

    return _embed_batch(client, base_url, texts)


def _embed_batch(client: httpx.Client, base_url: str, texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts."""
    response = client.post(
        f"{base_url}/embed",
        json={"texts": texts, "normalize": True},
    )
    response.raise_for_status()
    return response.json()["embeddings"]


def embed_single(text: str) -> list[float]:
    """Generate embedding for a single text string.

    Args:
        text: Single text string to embed

    Returns:
        Embedding vector as list of floats
    """
    result = embed([text])
    return result[0] if result else []


async def aembed(texts: list[str]) -> list[list[float]]:
    """Async embedding generation via API.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    base_url = settings.embedding_base_url.rstrip("/")

    # Batch requests to avoid overload
    batch_size = 32
    if len(texts) > batch_size:
        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                results.extend(await _aembed_batch(client, base_url, batch))
        return results

    async with httpx.AsyncClient(timeout=30.0) as client:
        return await _aembed_batch(client, base_url, texts)


async def _aembed_batch(client: httpx.AsyncClient, base_url: str, texts: list[str]) -> list[list[float]]:
    """Async embed a batch of texts."""
    response = await client.post(
        f"{base_url}/embed",
        json={"texts": texts, "normalize": True},
    )
    response.raise_for_status()
    return response.json()["embeddings"]


async def aembed_single(text: str) -> list[float]:
    """Async embedding for a single text string.

    Args:
        text: Single text string to embed

    Returns:
        Embedding vector as list of floats
    """
    result = await aembed([text])
    return result[0] if result else []


def preload_model() -> None:
    """Warm up the embedding service at server startup (API call health check)."""
    client = _get_client()
    base_url = settings.embedding_base_url.rstrip("/")
    try:
        response = client.get(f"{base_url}/health")
        response.raise_for_status()
        print(f"Embedding API ready: {base_url}")
    except Exception as e:
        print(f"Embedding API health check failed: {e}")


__all__ = [
    "embed",
    "embed_single",
    "aembed",
    "aembed_single",
    "preload_model",
]
