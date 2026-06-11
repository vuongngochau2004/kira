"""Citation verifier for validating LLM citations against retrieved documents."""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CitationStatus(Enum):
    """Status of a citation check."""
    VERIFIED = "verified"
    HALLUCINATED = "hallucinated"  # claimed source not in retrieved docs
    WEAK_GROUNDING = "weak_grounding"  # low similarity score
    MISSING = "missing"  # no citation for a claim


@dataclass
class CitationCheck:
    """Result of checking a single citation.

    Attributes:
        chunk_id: The chunk identifier that was checked
        status: Verification status (verified, hallucinated, weak_grounding)
        grounding_score: Similarity score (0-1) if calculated, None otherwise
        retrieved_position: Position in retrieved_docs list if found
    """
    chunk_id: str
    status: CitationStatus
    grounding_score: Optional[float] = None
    retrieved_position: Optional[int] = None


class CitationVerifier:
    """Verify LLM citations against retrieved documents.

    Checks:
    1. Chunk_id exists in retrieved documents
    2. Claim is grounded in chunk content (via similarity score)
    """

    def __init__(self, grounding_threshold: float = 0.7):
        """Initialize verifier.

        Args:
            grounding_threshold: Minimum similarity score for verified status (0-1)

        Raises:
            ValueError: If grounding_threshold is not between 0 and 1
        """
        if not 0.0 <= grounding_threshold <= 1.0:
            raise ValueError(
                f"grounding_threshold must be between 0.0 and 1.0, got {grounding_threshold}"
            )
        self.grounding_threshold = grounding_threshold

    def verify(
        self,
        parsed_citations: List,
        retrieved_docs: List[dict],
        response: str
    ) -> Dict[str, List[CitationCheck]]:
        """Verify all citations against retrieved documents.

        Args:
            parsed_citations: List of ParsedCitation objects from CitationParser
            retrieved_docs: List of retrieved document chunks
            response: Full LLM response text

        Returns:
            Dict with keys: 'verified', 'hallucinated', 'weak_grounding', 'missing'
            Each containing list of CitationCheck objects
        """
        if not parsed_citations or not retrieved_docs:
            logger.warning("No citations or retrieved docs to verify")
            return {
                "verified": [],
                "hallucinated": [],
                "weak_grounding": [],
                "missing": []
            }

        # Build set of retrieved chunk_ids for O(1) lookup
        retrieved_chunk_ids = {}
        for idx, doc in enumerate(retrieved_docs):
            chunk_id = doc.get("chunk_id", doc.get("id", ""))
            if chunk_id:
                # Normalize to first 8 chars (as used in parser)
                chunk_id_short = str(chunk_id)[:8]
                retrieved_chunk_ids[chunk_id_short] = idx

        # OPTIMIZATION: Batch compute all embeddings upfront to avoid N+1 calls
        # Collect unique contexts that need embedding
        unique_contexts = {}
        for citation in parsed_citations:
            if citation.context and citation.context not in unique_contexts:
                unique_contexts[citation.context] = []

        # Collect unique chunk texts that need embedding (not cached)
        unique_chunks = {}
        for citation in parsed_citations:
            chunk_id = citation.chunk_id[:8]
            if chunk_id in retrieved_chunk_ids:
                retrieved_idx = retrieved_chunk_ids[chunk_id]
                retrieved_doc = retrieved_docs[retrieved_idx]
                chunk_text = retrieved_doc.get("text", retrieved_doc.get("content", ""))
                # Only embed if not already cached
                if chunk_text and not retrieved_doc.get("embedding"):
                    if chunk_text not in unique_chunks:
                        unique_chunks[chunk_text] = []

        # Batch compute embeddings for all unique contexts
        context_embeddings = self._batch_embed(list(unique_contexts.keys())) if unique_contexts else {}

        # Batch compute embeddings for all unique chunks
        chunk_embeddings = self._batch_embed(list(unique_chunks.keys())) if unique_chunks else {}

        results = {
            "verified": [],
            "hallucinated": [],
            "weak_grounding": [],
            "missing": []
        }

        # Check each parsed citation (using cached embeddings)
        for citation in parsed_citations:
            chunk_id = citation.chunk_id[:8]  # Normalize length

            if chunk_id not in retrieved_chunk_ids:
                # Chunk_id not found in retrieved docs - hallucination
                results["hallucinated"].append(CitationCheck(
                    chunk_id=citation.chunk_id,
                    status=CitationStatus.HALLUCINATED,
                    grounding_score=None,
                    retrieved_position=None
                ))
                logger.warning(f"Hallucinated citation detected: {chunk_id}")
                continue

            # Chunk_id exists - check grounding
            retrieved_idx = retrieved_chunk_ids[chunk_id]
            retrieved_doc = retrieved_docs[retrieved_idx]

            grounding_score = self._check_grounding_cached(
                citation.context,
                retrieved_doc,
                context_embeddings,
                chunk_embeddings
            )

            if grounding_score >= self.grounding_threshold:
                results["verified"].append(CitationCheck(
                    chunk_id=citation.chunk_id,
                    status=CitationStatus.VERIFIED,
                    grounding_score=grounding_score,
                    retrieved_position=retrieved_idx
                ))
            else:
                results["weak_grounding"].append(CitationCheck(
                    chunk_id=citation.chunk_id,
                    status=CitationStatus.WEAK_GROUNDING,
                    grounding_score=grounding_score,
                    retrieved_position=retrieved_idx
                ))
                logger.warning(
                    f"Weak grounding for citation {chunk_id}: {grounding_score:.2f}"
                )

        return results

    def _batch_embed(self, texts: List[str]) -> Dict[str, List[float]]:
        """Batch compute embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            Dict mapping text to its embedding vector
        """
        if not texts:
            return {}

        try:
            from ingestion.embedding import embed_batch

            # Batch compute all embeddings
            embeddings = embed_batch(texts)

            # Return as dict for O(1) lookup
            return dict(zip(texts, embeddings))
        except ImportError:
            # Fallback to single embeddings if batch not available
            logger.warning("embed_batch not available, falling back to embed_single")
            from ingestion.embedding import embed_single

            result = {}
            for text in texts:
                result[text] = embed_single(text)
            return result
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            return {}

    def _check_grounding_cached(
        self,
        claim: str,
        retrieved_doc: dict,
        context_embeddings: Dict[str, List[float]],
        chunk_embeddings: Dict[str, List[float]]
    ) -> float:
        """Check if claim is grounded in retrieved chunk using cached embeddings.

        Args:
            claim: The claim sentence from response
            retrieved_doc: The retrieved document chunk
            context_embeddings: Pre-computed embeddings for contexts
            chunk_embeddings: Pre-computed embeddings for chunks

        Returns:
            Similarity score (0-1), 0.0 if calculation fails
        """
        try:
            from scipy.spatial.distance import cosine

            # Get chunk text
            chunk_text = retrieved_doc.get("text", retrieved_doc.get("content", ""))
            if not chunk_text:
                return 0.0

            # Get claim embedding from cache
            claim_embedding = context_embeddings.get(claim)
            if not claim_embedding:
                return 0.0

            # Get chunk embedding from cache or use cached from doc
            chunk_embedding = retrieved_doc.get("embedding")
            if not chunk_embedding:
                chunk_embedding = chunk_embeddings.get(chunk_text)
                if not chunk_embedding:
                    return 0.0

            # Calculate cosine similarity (1 - cosine distance)
            similarity = 1 - cosine(claim_embedding, chunk_embedding)
            return float(similarity)

        except Exception as e:
            logger.error(f"Grounding check failed: {e}")
            return 0.0

    def _check_grounding(
        self,
        claim: str,
        retrieved_doc: dict
    ) -> float:
        """Check if claim is grounded in retrieved chunk via similarity.

        Args:
            claim: The claim sentence from response
            retrieved_doc: The retrieved document chunk

        Returns:
            Similarity score (0-1), 0.0 if calculation fails
        """
        try:
            from ingestion.embedding import embed_single
            from scipy.spatial.distance import cosine

            # Get chunk text
            chunk_text = retrieved_doc.get("text", retrieved_doc.get("content", ""))
            if not chunk_text:
                return 0.0

            # Get embeddings
            claim_embedding = embed_single(claim)

            # Check if chunk has cached embedding
            chunk_embedding = retrieved_doc.get("embedding")
            if not chunk_embedding:
                # Compute chunk embedding if not cached
                chunk_embedding = embed_single(chunk_text)

            # Calculate cosine similarity (1 - cosine distance)
            similarity = 1 - cosine(claim_embedding, chunk_embedding)
            return float(similarity)

        except Exception as e:
            logger.error(f"Grounding check failed: {e}")
            return 0.0

    def get_summary_stats(self, verification_results: Dict[str, List[CitationCheck]]) -> dict:
        """Get summary statistics from verification results.

        Args:
            verification_results: Results from verify() method

        Returns:
            Dict with counts for each status
        """
        return {
            "verified": len(verification_results.get("verified", [])),
            "hallucinated": len(verification_results.get("hallucinated", [])),
            "weak_grounding": len(verification_results.get("weak_grounding", [])),
            "missing": len(verification_results.get("missing", [])),
            "total": sum(
                len(results)
                for results in verification_results.values()
            )
        }


__all__ = [
    "CitationStatus",
    "CitationCheck",
    "CitationVerifier",
]
