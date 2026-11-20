"""BM25 index manager for in-memory per-user indexes."""

from uuid import UUID

from kira.retrieval.bm25_index import BM25Index


class BM25IndexManager:
    """Manages in-memory BM25 indexes per user."""

    def __init__(self):
        """Initialize BM25 index manager."""
        self._indexes: dict[str, BM25Index] = {}
        # Signature of the persisted chunk set each index was rebuilt from. Any other
        # mutation drops it so the next search re-checks against the database.
        self._signatures: dict[str, object] = {}

    def _get_key(self, user_id: UUID | str) -> str:
        """Get cache key for user."""
        return str(user_id)

    def get_index(self, user_id: UUID | str) -> BM25Index:
        """Get or create BM25 index for user.

        Args:
            user_id: User ID

        Returns:
            BM25Index instance
        """
        key = self._get_key(user_id)
        if key not in self._indexes:
            self._indexes[key] = BM25Index()
        return self._indexes[key]

    def has_documents(self, user_id: UUID | str) -> bool:
        """Return True when the user's BM25 index has indexed chunks."""
        key = self._get_key(user_id)
        index = self._indexes.get(key)
        return bool(index and index.document_count > 0)

    def add_document(
        self,
        user_id: UUID | str,
        chunks: list[dict],
    ) -> None:
        """Add document chunks to user's BM25 index.

        Args:
            user_id: User ID
            chunks: List of chunk dicts with content and metadata
        """
        index = self.get_index(user_id)

        for chunk in chunks:
            index.add_document(
                content=chunk.get("content", ""),
                metadata=chunk.get("metadata", {}),
            )

    def add_document_bulk(
        self,
        user_id: UUID | str,
        chunks: list[dict],
    ) -> None:
        """Add document chunks to user's BM25 index in bulk.

        Args:
            user_id: User ID
            chunks: List of chunk dicts with content and metadata
        """
        index = self.get_index(user_id)
        index.index_documents(chunks)

    def remove_document(
        self,
        user_id: UUID | str,
        document_id: UUID | str,
    ) -> None:
        """Remove document from user's BM25 index.

        Note: This clears the entire index for simplicity.
        In production, implement proper deletion.

        Args:
            user_id: User ID
            document_id: Document ID to remove
        """
        key = self._get_key(user_id)
        self._signatures.pop(key, None)
        if key in self._indexes:
            # Clear the whole index; the next search rebuilds it from persisted chunks
            # because the signature is gone.
            self._indexes[key].clear()

    def clear_user(self, user_id: UUID | str) -> None:
        """Clear all indexes for a user.

        Args:
            user_id: User ID
        """
        key = self._get_key(user_id)
        self._signatures.pop(key, None)
        if key in self._indexes:
            del self._indexes[key]

    def get_signature(self, user_id: UUID | str) -> object:
        """Return the chunk-set signature the user's index was rebuilt from, if any."""
        return self._signatures.get(self._get_key(user_id))

    def rebuild_from_chunks(
        self,
        user_id: UUID | str,
        all_chunks: list[dict],
        signature: object = None,
    ) -> None:
        """Rebuild BM25 index from all user's chunks.

        Args:
            user_id: User ID
            all_chunks: All chunks for the user
            signature: Fingerprint of the persisted chunk set these chunks came from
        """
        index = self.get_index(user_id)
        index.clear()
        if all_chunks:
            index.index_documents(all_chunks)
        key = self._get_key(user_id)
        if signature is None:
            self._signatures.pop(key, None)
        else:
            self._signatures[key] = signature


# Global singleton
_bm25_manager = BM25IndexManager()


def get_bm25_manager() -> BM25IndexManager:
    """Get global BM25 index manager singleton."""
    return _bm25_manager


__all__ = ["BM25IndexManager", "get_bm25_manager"]
