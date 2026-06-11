"""Embedding API Adapter — implements EmbeddingPort using existing embedder.

Wraps the existing embed_single / aembed_single functions from
src.modules.document.domain.services.embedder to conform to EmbeddingPort.
"""
import asyncio
from src.shared.ports.embedding import EmbeddingPort


class EmbeddingAPIAdapter(EmbeddingPort):
    """Adapter: wraps embedder functions to conform to EmbeddingPort.

    Example:
        >>> adapter = EmbeddingAPIAdapter()
        >>> vector = await adapter.embed("Xin chào")
        >>> vectors = await adapter.embed_batch(["Xin chào", "Hello"])
    """

    def __init__(self, embedding_dim: int = 768):
        """Initialize with expected embedding dimension.

        Args:
            embedding_dim: Expected vector dimension (model-dependent)
        """
        self._dimension = embedding_dim

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: Input text to embed

        Returns:
            Dense vector as list of floats
        """
        from src.modules.document.domain.services.embedder import aembed_single
        return await aembed_single(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts concurrently.

        Args:
            texts: List of texts to embed

        Returns:
            List of dense vectors in same order as input
        """
        from src.modules.document.domain.services.embedder import aembed_single
        return await asyncio.gather(*[aembed_single(t) for t in texts])

    @property
    def dimension(self) -> int:
        """Return embedding vector dimension."""
        return self._dimension
