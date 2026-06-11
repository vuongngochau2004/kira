"""Citation parser for extracting inline citation markers from LLM responses."""

import re
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedCitation:
    """Represents a parsed citation from LLM response.

    Attributes:
        chunk_id: The chunk identifier (first 8 chars of UUID)
        position: Tuple of (start, end) character positions in response
        context: The sentence/context containing this citation marker
    """
    chunk_id: str
    position: Tuple[int, int]
    context: str


class CitationParser:
    """Parse citation markers from LLM response text.

    Expected format: [source:chunk_id] or [source:chunk_id1,chunk_id2]

    Example:
        "Theo điều khoản 5, bên A có quyền... [source:abc-123]"
    """

    # Pattern for [source:chunk_id] or [source:chunk_id1,chunk_id2]
    CITATION_PATTERN = r'\[source:([^\]]+)\]'

    # Sentence boundary pattern
    SENTENCE_BOUNDARY = r'[.!?。！？]\s+'

    def parse(self, response: str) -> List[ParsedCitation]:
        """Extract all citation markers from response.

        Args:
            response: The LLM response text

        Returns:
            List of ParsedCitation objects with position and context
        """
        # VALIDATION: Ensure response is a valid string
        if not response or not isinstance(response, str):
            logger.warning(f"Invalid response input: {type(response).__name__}")
            return []

        # Sanitize response - remove null bytes and control characters
        response = response.replace('\x00', '').strip()
        if not response:
            logger.warning("Response is empty after sanitization")
            return []

        citations = []

        try:
            for match in re.finditer(self.CITATION_PATTERN, response):
                chunk_ids_str = match.group(1)
                start, end = match.span()

                # Extract context sentence
                context = self._extract_context_sentence(response, start)

                # Handle multiple chunk_ids: [source:abc,def]
                for chunk_id in chunk_ids_str.split(','):
                    chunk_id = chunk_id.strip()
                    # VALIDATION: Ensure chunk_id is valid format
                    if not chunk_id:
                        continue
                    # Chunk_id should be alphanumeric with optional hyphens/underscores
                    if not re.match(r'^[a-zA-Z0-9_-]+$', chunk_id):
                        logger.warning(f"Invalid chunk_id format: {chunk_id}, skipping")
                        continue
                    citations.append(ParsedCitation(
                        chunk_id=chunk_id,
                        position=(start, end),
                        context=context
                    ))
        except Exception as e:
            logger.error(f"Error parsing citations: {e}")
            return []

        return citations

    def _extract_context_sentence(self, text: str, pos: int) -> str:
        """Extract the sentence containing the citation marker.

        Args:
            text: Full response text
            pos: Position of citation marker in text

        Returns:
            The sentence containing the citation
        """
        # VALIDATION: Ensure pos is within bounds
        if not text or pos < 0 or pos >= len(text):
            return ""

        # Find sentence boundaries
        start = text.rfind('. ', 0, pos) + 2
        if start == 1:  # No period found, start from beginning
            start = 0

        end = text.find('. ', pos)
        if end == -1:  # No period after, go to end
            end = len(text)

        return text[start:end].strip()

    def extract_uncited_claims(self, response: str) -> List[str]:
        """Detect sentences/claims without citations.

        This identifies potential hallucinations or missing attributions.

        Args:
            response: The LLM response text

        Returns:
            List of uncited sentences (potential issues)
        """
        # VALIDATION: Ensure response is valid
        if not response or not isinstance(response, str):
            logger.warning("Invalid response input for uncited claims extraction")
            return []

        # Sanitize response
        response = response.replace('\x00', '').strip()
        if not response:
            return []

        # Split into sentences
        sentences = re.split(self.SENTENCE_BOUNDARY, response)
        uncited = []

        # Meta sentences that don't require citations
        meta_patterns = [
            r'^theo\s',  # Already starts with "Theo" (follows)
            r'dựa\s+trên\s',  # "Dựa trên"
            r'tài\s+liệu\s',  # "Tài liệu"
            r'nguồn\s',  # "Nguồn"
            r'ngữ\s+cảnh\s',  # "Ngữ cảnh"
            r'thông\s+tin\s',  # "Thông tin"
            r'không\s+có\s',  # "Không có"
            r'xin\s+lỗi\s',  # "Xin lỗi"
            r'^xin\s+chào\s',  # Greetings
            r'^cảm\s+ơn\s',  # Thanks
            r'^chào\s+bạn\s',  # Hello
        ]

        try:
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                # Skip if has citation
                if re.search(self.CITATION_PATTERN, sentence):
                    continue

                # Check if it's a meta sentence that doesn't need citation
                is_meta = any(
                    re.search(pattern, sentence.lower())
                    for pattern in meta_patterns
                )

                if not is_meta and len(sentence) > 20:  # Only meaningful sentences
                    uncited.append(sentence)
        except Exception as e:
            logger.error(f"Error extracting uncited claims: {e}")
            return []

        return uncited

    def count_total_claims(self, response: str) -> int:
        """Count total claim sentences in response.

        Args:
            response: The LLM response text

        Returns:
            Total number of claim sentences
        """
        # VALIDATION: Ensure response is valid
        if not response or not isinstance(response, str):
            logger.warning("Invalid response input for counting claims")
            return 0

        # Split into sentences and filter out empty ones
        try:
            sentences = re.split(self.SENTENCE_BOUNDARY, response)
            return sum(1 for s in sentences if s.strip() and len(s.strip()) > 10)
        except Exception as e:
            logger.error(f"Error counting claims: {e}")
            return 0


__all__ = [
    "ParsedCitation",
    "CitationParser",
]
