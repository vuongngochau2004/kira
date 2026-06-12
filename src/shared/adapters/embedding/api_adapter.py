"""Embedding API adapter."""

import httpx

from src.config.config import settings
from src.shared.ports.embedding import EmbeddingPort


class EmbeddingAPIAdapter(EmbeddingPort):
    """Adapter that calls the configured embedding HTTP API."""

    def __init__(self, embedding_dim: int | None = None, timeout: float = 30.0):
        """Initialize with expected embedding dimension.

        Args:
            embedding_dim: Expected vector dimension (model-dependent)
            timeout: HTTP timeout in seconds
        """
        self._dimension = embedding_dim or settings.embedding_dim
        self._timeout = timeout

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: Input text to embed

        Returns:
            Dense vector as list of floats
        """
        result = await self.embed_batch([text])
        return result[0] if result else []

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts concurrently.

        Args:
            texts: List of texts to embed

        Returns:
            List of dense vectors in same order as input
        """
        if not texts:
            return []

        base_url = settings.embedding_base_url.rstrip("/")
        results: list[list[float]] = []
        batch_size = 32

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                response = await client.post(
                    f"{base_url}/embed",
                    json={"texts": batch, "normalize": True},
                )
                response.raise_for_status()
                results.extend(response.json()["embeddings"])

        return results

    async def health_check(self) -> bool:
        """Check embedding API health."""
        base_url = settings.embedding_base_url.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{base_url}/health")
                response.raise_for_status()
            return True
        except Exception:
            return False

    @property
    def dimension(self) -> int:
        """Return embedding vector dimension."""
        return self._dimension
