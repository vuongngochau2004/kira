"""TEI (Hugging Face Text Embeddings Inference) adapter for DUT AI.

Implements EmbeddingPort for BAAI/bge-m3 via TEI inference server.
Supports both TEI native (/embed) and OpenAI-compatible (/v1/embeddings) endpoints.
"""

import logging

import httpx

from src.config.config import settings
from src.shared.ports.embedding import EmbeddingPort

logger = logging.getLogger(__name__)


class TEIEmbeddingAdapter(EmbeddingPort):
    """Adapter for DUT AI / HuggingFace Text Embeddings Inference (TEI)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        embedding_dim: int | None = None,
        timeout: float = 30.0,
    ):
        """Initialize TEI embedding adapter.

        Args:
            base_url: TEI server base URL
            api_key: Bearer token for authentication
            model: Model name (e.g. BAAI/bge-m3)
            embedding_dim: Expected embedding dimension (default: 1024)
            timeout: Request timeout in seconds
        """
        self._base_url = (base_url or settings.tei_base_url).rstrip("/")
        self._api_key = api_key or settings.tei_api_key
        self._model = model or settings.tei_embedding_model
        self._dimension = embedding_dim or settings.tei_embedding_dim
        self._timeout = timeout

    def _get_headers(self) -> dict[str, str]:
        """Build request headers with auth token."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

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
        """Embed multiple texts concurrently using batch requests.

        Args:
            texts: List of texts to embed

        Returns:
            List of dense vectors in same order as input
        """
        if not texts:
            return []

        results: list[list[float]] = []
        batch_size = 32
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                batch_embeddings = await self._call_tei_embed(client, batch, headers)
                results.extend(batch_embeddings)

        return results

    async def _call_tei_embed(
        self,
        client: httpx.AsyncClient,
        batch: list[str],
        headers: dict[str, str],
    ) -> list[list[float]]:
        """Call TEI /embed endpoint with fallback to /v1/embeddings."""
        # 1. Try native TEI endpoint: POST /embed
        native_url = f"{self._base_url}/embed"
        payload = {"inputs": batch, "normalize": True}
        try:
            response = await client.post(native_url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "embeddings" in data:
                    return data["embeddings"]
            logger.debug(
                "TEI /embed returned status %d, falling back to /v1/embeddings",
                response.status_code,
            )
        except httpx.HTTPError as e:
            logger.debug("TEI native /embed call failed (%s), trying /v1/embeddings", e)

        # 2. Fallback to OpenAI-compatible endpoint: POST /v1/embeddings
        compat_url = f"{self._base_url}/v1/embeddings"
        compat_payload = {"model": self._model, "input": batch}
        response = await client.post(compat_url, json=compat_payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    async def health_check(self) -> bool:
        """Check TEI service availability.

        Returns:
            True if healthy, False otherwise
        """
        headers = self._get_headers()
        endpoints = [
            f"{self._base_url}/health/embedding",
            f"{self._base_url}/health",
            f"{self._base_url}/info",
        ]
        try:
            async with httpx.AsyncClient(timeout=min(self._timeout, 5.0)) as client:
                for endpoint in endpoints:
                    try:
                        resp = await client.get(endpoint, headers=headers)
                        if resp.status_code == 200:
                            return True
                    except httpx.HTTPError:
                        continue
            return False
        except Exception:
            return False

    @property
    def dimension(self) -> int:
        """Return embedding vector dimension."""
        return self._dimension

