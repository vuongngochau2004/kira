"""BM25 sparse keyword retrieval with Vietnamese text tokenization."""

import math
import re
import unicodedata
from collections import Counter


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

__all__ = [
    "BM25Index",
    "normalize_text",
    "tokenize_text",
    "_normalize",
    "_tokenize",
]
