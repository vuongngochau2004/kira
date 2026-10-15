"""Compatibility functions backed by the configured embedding adapter."""

import asyncio

from src.shared.adapters.embedding import create_embedding_adapter


def embed(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts via API.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    return asyncio.run(aembed(texts))


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

    return await create_embedding_adapter().embed_batch(texts)


async def aembed_single(text: str) -> list[float]:
    """Async embedding for a single text string.

    Args:
        text: Single text string to embed

    Returns:
        Embedding vector as list of floats
    """
    result = await aembed([text])
    return result[0] if result else []


__all__ = [
    "embed",
    "embed_single",
    "aembed",
    "aembed_single",
]
