"""BM25 keyword search: Vietnamese tokenizer, per-user in-memory indexes and their manager."""

import math
import re
import unicodedata
from collections import Counter
from uuid import UUID


def normalize_text(text: str) -> str:
    """Normalize text: NFC unicode normalization + whitespace cleanup."""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize_text(text: str) -> list[str]:
    """Tokenize Vietnamese text using PyVi or fallback to whitespace split."""
    normalized = normalize_text(text)
    try:
        from pyvi import ViTokenizer

        tokenized = ViTokenizer.tokenize(normalized)
    except ImportError:
        tokenized = normalized
    return tokenized.lower().split()


class BM25Index:
    """BM25 index for keyword-based document retrieval."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """Initialize BM25 index.

        Args:
            k1: Term frequency saturation parameter
            b: Length normalization parameter
        """
        self.k1 = k1
        self.b = b
        self.doc_freqs: list[dict[str, int]] = []
        self.idf: dict[str, float] = {}
        self.doc_texts: list[str] = []
        self.doc_metadata: list[dict] = []
        self.avg_doc_len: float = 0.0

    @property
    def document_count(self) -> int:
        """Return number of documents currently indexed."""
        return len(self.doc_texts)

    def index_documents(self, documents: list[dict]) -> None:
        """Index documents for BM25 retrieval.

        Args:
            documents: List of dicts with content and metadata
        """
        self.doc_freqs = []
        self.doc_texts = []
        self.doc_metadata = []

        for doc in documents:
            text = doc.get("content", doc.get("text", ""))
            tokens = tokenize_text(text)
            freq = Counter(tokens)
            self.doc_freqs.append(dict(freq))
            self.doc_texts.append(text)
            self.doc_metadata.append(doc.get("metadata", {}))

        self._compute_idf()

    def _compute_idf(self) -> None:
        """Compute inverse document frequency for all terms."""
        n_docs = len(self.doc_freqs)
        if n_docs == 0:
            return

        doc_len_sum = sum(len(f) for f in self.doc_freqs)
        self.avg_doc_len = float(doc_len_sum) / n_docs

        df: dict[str, int] = {}
        for doc_term_freq in self.doc_freqs:
            for term in doc_term_freq:
                df[term] = df.get(term, 0) + 1

        for term, term_freq in df.items():
            self.idf[term] = math.log((n_docs - term_freq + 0.5) / (term_freq + 0.5) + 1)

    def search(self, query: str, k: int = 5) -> list[dict]:
        """Search for documents using BM25 scoring.

        Args:
            query: Query text
            k: Number of results to return

        Returns:
            List of relevant documents with content and metadata
        """
        tokens = tokenize_text(query)

        if not tokens or not self.doc_freqs:
            return []

        scores = []
        for idx, freq in enumerate(self.doc_freqs):
            doc_len = len(freq)
            score = 0.0

            for token in tokens:
                if token not in freq:
                    continue

                tf = freq[token]
                idf = self.idf.get(token, 0)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
                score += idf * (numerator / denominator)

            scores.append((idx, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scores[:k]:
            metadata = self.doc_metadata[idx]
            results.append(
                {
                    "text": self.doc_texts[idx],
                    "content": self.doc_texts[idx],
                    "metadata": metadata,
                    "document_id": metadata.get("document_id"),
                    "chunk_index": metadata.get("chunk_index"),
                    "score": score,
                }
            )

        return results

    def add_document(self, content: str, metadata: dict) -> None:
        """Add a single document to the index."""
        tokens = tokenize_text(content)
        freq = Counter(tokens)
        self.doc_freqs.append(dict(freq))
        self.doc_texts.append(content)
        self.doc_metadata.append(metadata)
        self._compute_idf()

    def remove_document(self, index: int) -> None:
        """Remove a document from the index by position."""
        if 0 <= index < len(self.doc_freqs):
            self.doc_freqs.pop(index)
            self.doc_texts.pop(index)
            self.doc_metadata.pop(index)
            self._compute_idf()

    def clear(self) -> None:
        """Clear all documents from the index."""
        self.doc_freqs = []
        self.idf = {}
        self.doc_texts = []
        self.doc_metadata = []
        self.avg_doc_len = 0


# Backward-compatible private aliases
_normalize = normalize_text


_tokenize = tokenize_text


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


class BM25KeywordIndexAdapter:
    """Adapter around the in-memory BM25 index manager."""

    def __init__(self, manager: BM25IndexManager):
        """Initialize adapter with a concrete BM25 manager."""
        self.manager = manager

    async def add_document_bulk(self, user_id: UUID | str, chunks: list[dict]) -> None:
        """Add document chunks to the user's keyword index."""
        self.manager.add_document_bulk(user_id=user_id, chunks=chunks)

    async def remove_document(self, user_id: UUID | str, document_id: UUID | str) -> None:
        """Remove a document from the user's keyword index."""
        self.manager.remove_document(user_id=user_id, document_id=document_id)
