"""BM25 keyword index for sparse retrieval."""

import math
import re
import unicodedata
from collections import Counter
from typing import Any


def _normalize(text: str) -> str:
    """Normalize text: NFC unicode normalization + whitespace cleanup."""
    # Unicode normalization
    text = unicodedata.normalize("NFC", text)
    # Normalize whitespace: multiple spaces/tabs/newlines -> single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokenize(text: str) -> list[str]:
    """Simple whitespace tokenization for Vietnamese."""
    normalized = _normalize(text)
    return normalized.lower().split()


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
        self.avg_doc_len = 0

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
            tokens = _tokenize(text)
            freq = Counter(tokens)
            self.doc_freqs.append(dict(freq))
            self.doc_texts.append(text)
            self.doc_metadata.append(doc.get("metadata", {}))

        # Compute IDF
        self._compute_idf()

    def _compute_idf(self) -> None:
        """Compute inverse document frequency for all terms."""
        n_docs = len(self.doc_freqs)
        if n_docs == 0:
            return

        doc_len_sum = sum(len(freq) for freq in self.doc_freqs)
        self.avg_doc_len = doc_len_sum / n_docs

        # Count document frequency for each term
        df: dict[str, int] = {}
        for freq in self.doc_freqs:
            for term in freq:
                df[term] = df.get(term, 0) + 1

        # Compute IDF using standard BM25 formula
        for term, freq in df.items():
            self.idf[term] = math.log((n_docs - freq + 0.5) / (freq + 0.5) + 1)

    def search(self, query: str, k: int = 5) -> list[dict]:
        """Search for documents using BM25 scoring.

        Args:
            query: Query text
            k: Number of results to return

        Returns:
            List of relevant documents with content and metadata
        """
        tokens = _tokenize(query)

        if not tokens or not self.doc_freqs:
            return []

        scores = []
        for idx, freq in enumerate(self.doc_freqs):
            doc_len = len(freq)
            score = 0.0

            for token in tokens:
                if token not in freq:
                    continue

                # BM25 score formula
                tf = freq[token]
                idf = self.idf.get(token, 0)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
                score += idf * (numerator / denominator)

            scores.append((idx, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return top-k documents
        results = []
        for idx, score in scores[:k]:
            results.append({
                "content": self.doc_texts[idx],
                "metadata": self.doc_metadata[idx],
                "score": score,
            })

        return results

    def add_document(self, content: str, metadata: dict) -> None:
        """Add a single document to the index.

        Args:
            content: Document content
            metadata: Document metadata
        """
        tokens = _tokenize(content)
        freq = Counter(tokens)
        self.doc_freqs.append(dict(freq))
        self.doc_texts.append(content)
        self.doc_metadata.append(metadata)
        # Recompute IDF (inefficient but simple)
        self._compute_idf()

    def remove_document(self, index: int) -> None:
        """Remove a document from the index by position.

        Args:
            index: Document index to remove
        """
        if 0 <= index < len(self.doc_freqs):
            self.doc_freqs.pop(index)
            self.doc_texts.pop(index)
            self.doc_metadata.pop(index)
            # Recompute IDF
            self._compute_idf()

    def clear(self) -> None:
        """Clear all documents from the index."""
        self.doc_freqs = []
        self.idf = {}
        self.doc_texts = []
        self.doc_metadata = []
        self.avg_doc_len = 0


__all__ = ["BM25Index", "_tokenize", "_normalize"]
