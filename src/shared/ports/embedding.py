"""Port: Embedding model contract.

Application core depends on this ABC, NOT on a specific embedding model.
Allows swapping Vietnamese-v2 ↔ BAAI/bge ↔ OpenAI text-embedding-3
without changing business logic.
"""
from abc import ABC, abstractmethod


class EmbeddingPort(ABC):
    """Port: what the application needs from any embedding model.

    Example:
        >>> class MyEmbedder(EmbeddingPort):
        ...     async def embed(self, text: str) -> list[float]:
        ...         return [0.1, 0.2, ...]
        ...     async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...         return [[0.1, 0.2, ...], ...]
        ...     @property
        ...     def dimension(self) -> int:
        ...         return 768
    """

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Embed a single text string into a dense vector.

        Args:
            text: Text to embed

        Returns:
            Dense vector representation as list of floats
        """
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single batch call (more efficient).

        Args:
            texts: List of texts to embed

        Returns:
            List of dense vectors in the same order as input texts
        """
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension of embeddings produced by this model.

        Returns:
            Integer dimension (e.g. 768, 1024, 1536)
        """
        ...
