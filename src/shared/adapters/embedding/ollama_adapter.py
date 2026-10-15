"""Ollama implementation of the embedding port."""

import httpx

from src.config.config import settings
from src.shared.ports.embedding import EmbeddingPort


class OllamaEmbeddingAdapter(EmbeddingPort):
    """Generate embeddings through Ollama's ``/api/embed`` endpoint."""

    def __init__(self, embedding_dim: int | None = None, timeout: float = 30.0):
        self._dimension = embedding_dim or settings.embedding_dim
        self._timeout = timeout

    async def embed(self, text: str) -> list[float]:
        embeddings = await self.embed_batch([text])
        return embeddings[0] if embeddings else []

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{settings.embedding_base_url.rstrip('/')}/embed",
                headers=self._headers(),
                json={
                    "model": settings.embedding_model,
                    "input": texts,
                    "dimensions": self._dimension,
                },
            )
            response.raise_for_status()
            embeddings = response.json()["embeddings"]

        if any(len(vector) != self._dimension for vector in embeddings):
            raise ValueError(
                f"Ollama returned an embedding dimension different from {self._dimension}."
            )
        return embeddings

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    f"{settings.embedding_base_url.rstrip('/')}/tags",
                    headers=self._headers(),
                )
                response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    @property
    def dimension(self) -> int:
        return self._dimension

    @staticmethod
    def _headers() -> dict[str, str]:
        api_key = settings.ollama_api_keys.split(",", 1)[0].strip()
        return {"Authorization": f"Bearer {api_key}"} if api_key else {}
