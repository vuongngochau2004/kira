"""
Keyword-based classification strategy.

Fast classification using fuzzy file matching and keyword detection.
"""

import re
from typing import Any
from uuid import UUID

from src.shared.ports.classification import ClassificationStrategyBase, ClassificationResult, Intent
from src.shared.ports.retrieval import Document


class KeywordStrategy(ClassificationStrategyBase):
    """
    Fast keyword-based classification strategy.

    Uses fuzzy file matching and keyword detection to classify queries.
    Target latency: <5ms (p95).

    Attributes:
        user_documents: User-specific document mapping
        file_keywords: Keywords indicating file/document queries
        fuzzy_threshold: Minimum similarity score for fuzzy matching

    Example:
        >>> strategy = KeywordStrategy(user_documents={"user123": [Document(...)]})
        >>> result = await strategy.classify("hỏi về contract.pdf", "user123")
        >>> assert result.intent == Intent.RAG
    """

    def __init__(
        self,
        user_documents: dict[str, list[Document]] | None = None,
        file_keywords: list[str] | None = None,
        fuzzy_threshold: float = 0.6
    ):
        """
        Initialize keyword strategy.

        Args:
            user_documents: User-specific document mapping (user_id -> documents)
            file_keywords: Keywords indicating file queries (default: Vietnamese keywords)
            fuzzy_threshold: Minimum similarity for fuzzy matching (0.0 to 1.0)
        """
        self.user_documents = user_documents or {}
        self.file_keywords = file_keywords or [
            "tài liệu", "doc", "pdf", "file", "hỏi về",
            "trong", "có", "liên quan", "về", "chương",
            "mục", "điều", "khoản", "bản", "phụ lục"
        ]
        self.fuzzy_threshold = fuzzy_threshold

    def can_handle(self, query: str, user_id: str | UUID) -> bool:
        """
        Quick check if strategy can handle the query.

        Args:
            query: User query string
            user_id: User ID

        Returns:
            True if query looks like a file/document query
        """
        if not query or not query.strip():
            return False

        query_lower = query.lower()

        # Check for file keywords
        for keyword in self.file_keywords:
            if keyword in query_lower:
                return True

        return False

    async def classify(
        self,
        query: str,
        user_id: str | UUID,
        context: dict[str, Any] | None = None
    ) -> ClassificationResult:
        """
        Classify query using keyword matching.

        Args:
            query: User query string
            user_id: User ID
            context: Additional context (ignored for keyword strategy)

        Returns:
            ClassificationResult with intent and confidence
        """
        user_id_str = str(user_id)

        # 1. Check for file keywords
        keyword_match = self._detect_keywords(query)

        # 2. Try fuzzy filename matching
        matched_file = self._match_filename(query, user_id_str)

        # 3. Calculate confidence based on matches
        if matched_file:
            confidence = 0.95
            reason = f"Fuzzy filename match: {matched_file}"
        elif keyword_match:
            confidence = 0.85
            reason = f"Keyword detected: {keyword_match}"
        else:
            confidence = 0.3
            reason = "No keywords or file matches"

        # 4. Determine intent
        intent = Intent.RAG if confidence > 0.5 else Intent.CONVERSATIONAL

        return ClassificationResult(
            intent=intent,
            confidence=confidence,
            reason=reason,
            metadata={
                "strategy": "keyword",
                "matched_file": matched_file,
                "keyword_match": keyword_match,
                "user_doc_count": len(self.user_documents.get(user_id_str, []))
            },
            handler_hint="RAGHandler" if intent == Intent.RAG else "ConversationalHandler"
        )

    def _detect_keywords(self, query: str) -> str | None:
        """
        Detect file-related keywords in query.

        Args:
            query: User query string

        Returns:
            First matched keyword or None
        """
        query_lower = query.lower()

        for keyword in self.file_keywords:
            if keyword in query_lower:
                return keyword

        return None

    def _match_filename(self, query: str, user_id: str) -> str | None:
        """
        Fuzzy match query against user's filenames.

        Args:
            query: User query string
            user_id: User ID

        Returns:
            Matched filename or None
        """
        user_docs = self.user_documents.get(user_id, [])

        if not user_docs:
            return None

        query_lower = query.lower()

        # Try exact match first
        for doc in user_docs:
            filename = doc.filename if isinstance(doc, Document) else doc
            filename_lower = filename.lower()

            if filename_lower in query_lower:
                return filename

        # Try fuzzy match (simple substring for now)
        for doc in user_docs:
            filename = doc.filename if isinstance(doc, Document) else doc
            filename_lower = filename.lower()

            # Remove extension for matching
            filename_without_ext = filename_lower.rsplit(".", 1)[0]

            # Check if filename appears in query
            if filename_without_ext and filename_without_ext in query_lower:
                return filename

        return None

    def update_user_documents(self, user_id: str, documents: list[Document]) -> None:
        """
        Update user's document list.

        Args:
            user_id: User ID
            documents: List of documents for the user

        Example:
            >>> strategy.update_user_documents("user123", [Document(...)])
        """
        self.user_documents[user_id] = documents

    def add_document(self, user_id: str, document: Document) -> None:
        """
        Add a document for a user.

        Args:
            user_id: User ID
            document: Document to add
        """
        if user_id not in self.user_documents:
            self.user_documents[user_id] = []

        self.user_documents[user_id].append(document)

    def remove_document(self, user_id: str, filename: str) -> bool:
        """
        Remove a document for a user.

        Args:
            user_id: User ID
            filename: Filename to remove

        Returns:
            True if document was removed, False if not found
        """
        if user_id not in self.user_documents:
            return False

        docs = self.user_documents[user_id]
        original_length = len(docs)

        self.user_documents[user_id] = [
            doc for doc in docs
            if (doc.filename if isinstance(doc, Document) else doc) != filename
        ]

        return len(self.user_documents[user_id]) < original_length
