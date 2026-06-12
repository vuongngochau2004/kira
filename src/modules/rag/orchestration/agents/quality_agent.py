"""
QualityAgent: Merged critique + verification (4-agent architecture)

This agent consolidates quality assessment functionality:
- CritiqueAgent: Response quality evaluation and improvement suggestions
- VerificationAgent: Factual consistency and citation accuracy verification

Architecture:
    Input: RAGState (generated_response, retrieved_docs)
    Stage 1: Critique (quality assessment, issue detection)
    Stage 2: Verification (factual consistency, citation accuracy)
    Output: RAGState with quality_agent_output

Example:
    agent = QualityAgent(config=QualityAgentConfig(), llm_client=llm)
    state = await agent.handle(state)
    quality_score = get_quality_score(state)
"""

import logging
from typing import List, Dict, Any, AsyncIterator, Optional
import re
import time

from src.shared.ports.llm import LLMPort
from src.modules.rag.orchestration.state.rag_state import (
    RAGState,
    AgentStatus,
    CritiqueResult,
    VerificationResult,
    QualityScore,
    QualityAgentConfig,
    create_agent_result,
    mark_agent_start,
    update_state_with_agent_result,
    update_quality_output,
    get_retrieval_docs
)

logger = logging.getLogger(__name__)


class QualityAgent:
    """
    Unified quality agent merging critique and verification.

    Merged functionality from:
    - CritiqueAgent: Response quality evaluation
    - VerificationAgent: Factual consistency verification

    This consolidation provides unified quality control with comprehensive
    assessment across multiple dimensions.

    Attributes:
        config: QualityAgentConfig with merged settings
        llm_client: LLM client for critique and verification
    """

    def __init__(self, config: QualityAgentConfig, llm_client: Optional[LLMPort] = None):
        """
        Initialize QualityAgent.

        Args:
            config: Merged configuration from CritiqueAgent + VerificationAgent
            llm_client: Optional LLM client for quality assessment
        """
        self.config = config
        self.llm_client = llm_client
        self._iteration = 0

    async def handle(
        self,
        state: RAGState,
        context: Optional[Dict[str, Any]] = None
    ) -> RAGState:
        """
        Execute quality assessment: critique + verification.

        This is the main entry point for quality evaluation. It runs both
        critique and verification, then combines results into unified score.

        Args:
            state: Current RAGState with generated_response
            context: Optional additional context

        Returns:
            Updated RAGState with quality_agent_output populated
        """
        start_time = time.time()
        state = mark_agent_start(state, "QualityAgent")

        try:
            response = state["generated_response"]
            documents = get_retrieval_docs(state)
            query = state["query"]

            if not response:
                raise ValueError("No response to evaluate")

            logger.info(f"QualityAgent starting: response_length={len(response)}, docs={len(documents)}")

            # Stage 1: Critique (merged from CritiqueAgent)
            critique_result = await self._critique_response(query, response, documents)
            logger.info(f"Critique: quality={critique_result.quality_level.value}, confidence={critique_result.confidence_score:.2f}")

            # Stage 2: Verification (merged from VerificationAgent)
            verification_result = await self._verify_response(query, response, documents, critique_result)
            logger.info(f"Verification: verified={verification_result.is_verified}, confidence={verification_result.confidence:.2f}")

            # Calculate unified quality score
            quality_score = self._calculate_quality_score(critique_result, verification_result)

            # Determine if regeneration is needed
            should_regenerate = self._should_regenerate(critique_result, verification_result, quality_score)

            # Extract suggestions from both
            suggestions = critique_result.suggestions + [
                f"Factual consistency: {verification_result.factual_consistency:.2f}",
                f"Citation accuracy: {verification_result.citation_accuracy:.2f}"
            ]

            # Update state
            state = update_quality_output(
                state=state,
                quality_score=quality_score,
                critique=critique_result,
                verification=verification_result,
                suggestions=suggestions,
                should_regenerate=should_regenerate
            )

            execution_time = (time.time() - start_time) * 1000
            result = create_agent_result(
                agent_name="QualityAgent",
                status=AgentStatus.COMPLETED,
                execution_time_ms=execution_time,
                metadata={
                    "quality_score": quality_score,
                    "critique_quality": critique_result.quality_level.value,
                    "verification_passed": verification_result.is_verified,
                    "should_regenerate": should_regenerate,
                    "issues_count": len(critique_result.issues)
                }
            )

            logger.info(f"QualityAgent completed in {execution_time:.0f}ms: score={quality_score:.2f}, regenerate={should_regenerate}")
            return update_state_with_agent_result(state, result)

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"QualityAgent failed: {e}", exc_info=True)

            result = create_agent_result(
                agent_name="QualityAgent",
                status=AgentStatus.FAILED,
                execution_time_ms=execution_time,
                error_message=str(e)
            )

            # Set default quality output on failure
            state = update_quality_output(
                state=state,
                quality_score=0.5,
                should_regenerate=False
            )
            return update_state_with_agent_result(state, result)

    async def handle_stream(
        self,
        state: RAGState,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute quality assessment with streaming progress.

        Args:
            state: Current RAGState
            context: Optional additional context

        Yields:
            Streaming chunks with quality assessment progress
        """
        start_time = time.time()
        state = mark_agent_start(state, "QualityAgent")

        try:
            response = state["generated_response"]
            documents = get_retrieval_docs(state)
            query = state["query"]

            yield {"type": "stage", "data": {"stage": "critique", "status": "started"}}

            # Stage 1: Critique
            critique_result = await self._critique_response(query, response, documents)

            yield {
                "type": "stage",
                "data": {
                    "stage": "critique",
                    "status": "completed",
                    "quality": critique_result.quality_level.value,
                    "issues": len(critique_result.issues)
                }
            }

            # Stage 2: Verification
            yield {"type": "stage", "data": {"stage": "verification", "status": "started"}}

            verification_result = await self._verify_response(query, response, documents, critique_result)

            # Calculate unified score
            quality_score = self._calculate_quality_score(critique_result, verification_result)
            should_regenerate = self._should_regenerate(critique_result, verification_result, quality_score)

            state = update_quality_output(
                state=state,
                quality_score=quality_score,
                critique=critique_result,
                verification=verification_result,
                should_regenerate=should_regenerate
            )

            execution_time = (time.time() - start_time) * 1000
            result = create_agent_result(
                agent_name="QualityAgent",
                status=AgentStatus.COMPLETED,
                execution_time_ms=execution_time
            )
            state = update_state_with_agent_result(state, result)

            yield {
                "type": "stage",
                "data": {
                    "stage": "verification",
                    "status": "completed",
                    "verified": verification_result.is_verified,
                    "confidence": verification_result.confidence
                }
            }

            yield {
                "type": "quality",
                "data": {
                    "quality_score": quality_score,
                    "should_regenerate": should_regenerate,
                    "suggestions": critique_result.suggestions
                }
            }

        except Exception as e:
            logger.error(f"QualityAgent streaming failed: {e}")
            yield {"type": "error", "data": {"message": str(e)}}

    def can_handle(self, state: RAGState) -> bool:
        """
        Check if quality agent can handle the current state.

        QualityAgent requires a generated response to evaluate.

        Args:
            state: Current RAGState

        Returns:
            True if state has generated_response
        """
        return bool(state.get("generated_response"))

    # ==========================================================================
    # Stage 1: Critique (merged from CritiqueAgent)
    # ==========================================================================

    async def _critique_response(
        self,
        query: str,
        response: str,
        documents: List[Any]
    ) -> CritiqueResult:
        """
        Perform LLM-based critique of response.

        TODO: Implement comprehensive LLM critique with detailed prompting.

        Args:
            query: Original query
            response: Generated response
            documents: Retrieved documents

        Returns:
            CritiqueResult with quality assessment
        """
        if not self.config.enable_critique or not self.llm_client:
            # Return default positive result
            return CritiqueResult(
                quality_level=QualityScore.GOOD,
                confidence_score=0.8,
                issues=[],
                suggestions=[],
                should_regenerate=False
            )

        # TODO: Implement LLM-based critique
        # For now, use rule-based critique
        return self._rule_based_critique(response, documents)

    def _rule_based_critique(self, response: str, documents: List[Any]) -> CritiqueResult:
        """
        Rule-based critique fallback.

        TODO: Enhance with more sophisticated rules and patterns.

        Args:
            response: Generated response
            documents: Retrieved documents

        Returns:
            CritiqueResult based on heuristic rules
        """
        issues = self._check_response_issues(response, documents)
        suggestions = self._generate_suggestions(issues)

        # Determine quality level
        if len(issues) == 0:
            quality = QualityScore.GOOD
            confidence = 0.8
        elif len(issues) <= 2:
            quality = QualityScore.ACCEPTABLE
            confidence = 0.6
        else:
            quality = QualityScore.POOR
            confidence = 0.4

        return CritiqueResult(
            quality_level=quality,
            confidence_score=confidence,
            issues=issues,
            suggestions=suggestions,
            should_regenerate=len(issues) > 2
        )

    def _check_response_issues(self, response: str, documents: List[Any]) -> List[str]:
        """
        Check for common response issues.

        TODO: Add more sophisticated issue detection patterns.

        Args:
            response: Generated response
            documents: Retrieved documents

        Returns:
            List of identified issues
        """
        issues = []

        # Check length
        if len(response) < 50:
            issues.append("Response too short")
        elif len(response) > 5000:
            issues.append("Response too long")

        # Check citations
        if not re.search(r'\[Document\s+\d+\]', response):
            issues.append("No document citations")

        # Check for Vietnamese
        if not re.search(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]', response):
            issues.append("No Vietnamese characters detected")

        # Check for apology without useful info
        apology_patterns = [r'xin lỗi', r'không có thông tin']
        if any(re.search(p, response, re.IGNORECASE) for p in apology_patterns):
            issues.append("Response is just an apology")

        return issues

    def _generate_suggestions(self, issues: List[str]) -> List[str]:
        """
        Generate improvement suggestions based on issues.

        TODO: Implement contextual suggestion generation.

        Args:
            issues: List of identified issues

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        if "Response too short" in issues:
            suggestions.append("Provide more detailed response")
        if "No document citations" in issues:
            suggestions.append("Add proper document citations")
        if "No Vietnamese characters detected" in issues:
            suggestions.append("Use Vietnamese language")

        return suggestions

    # ==========================================================================
    # Stage 2: Verification (merged from VerificationAgent)
    # ==========================================================================

    async def _verify_response(
        self,
        query: str,
        response: str,
        documents: List[Any],
        critique_result: CritiqueResult
    ) -> VerificationResult:
        """
        Verify factual consistency and citation accuracy.

        TODO: Implement LLM-based factual consistency verification.

        Args:
            query: Original query
            response: Generated response
            documents: Retrieved documents
            critique_result: Critique result for context

        Returns:
            VerificationResult with detailed verification
        """
        if not self.config.enable_verification or not self.llm_client:
            # Return default positive result
            return VerificationResult(
                is_verified=True,
                confidence=0.8,
                factual_consistency=0.8,
                citation_accuracy=0.8,
                reasoning_quality=0.8,
                verification_checks=["Verification disabled - auto-verified"]
            )

        # Perform verification checks
        checks = []

        # Factual consistency
        factual_score = await self._verify_factual_consistency(query, response, documents)
        checks.append(f"Factual consistency: {factual_score:.2f}")

        # Citation accuracy
        citation_score = self._verify_citation_accuracy(response, documents)
        checks.append(f"Citation accuracy: {citation_score:.2f}")

        # Reasoning quality
        reasoning_score = self._assess_reasoning_quality(response)
        checks.append(f"Reasoning quality: {reasoning_score:.2f}")

        # Calculate overall confidence
        confidence = (factual_score * 0.4 + citation_score * 0.3 + reasoning_score * 0.3)

        return VerificationResult(
            is_verified=confidence >= self.config.verification_threshold,
            confidence=confidence,
            factual_consistency=factual_score,
            citation_accuracy=citation_score,
            reasoning_quality=reasoning_score,
            verification_checks=checks
        )

    async def _verify_factual_consistency(
        self,
        query: str,
        response: str,
        documents: List[Any]
    ) -> float:
        """
        Verify factual consistency using heuristic checks.

        TODO: Implement LLM-based factual verification for better accuracy.

        Args:
            query: Original query
            response: Generated response
            documents: Retrieved documents

        Returns:
            Factual consistency score (0-1)
        """
        # TODO: Implement LLM-based verification
        # For now, use heuristic
        score = 0.7

        # Check for citations
        if re.search(r'\[Document\s+\d+\]', response):
            score += 0.1

        # Check for uncertainty indicators (lower score)
        uncertainty_count = sum(
            1 for p in [r'có thể', r'có lẽ']
            if re.search(p, response, re.IGNORECASE)
        )
        score -= min(0.2, uncertainty_count * 0.05)

        return max(0.0, min(1.0, score))

    def _verify_citation_accuracy(self, response: str, documents: List[Any]) -> float:
        """
        Verify citation accuracy.

        TODO: Implement more sophisticated citation validation.

        Args:
            response: Generated response
            documents: Retrieved documents

        Returns:
            Citation accuracy score (0-1)
        """
        if not documents:
            return 0.5

        score = 1.0
        num_docs = len(documents)

        # Extract cited document numbers
        cited_docs = set()
        for match in re.finditer(r'\[Document\s+(\d+)\]', response):
            try:
                doc_num = int(match.group(1))
                cited_docs.add(doc_num)
            except ValueError:
                pass

        # Validate citation range
        for doc_num in cited_docs:
            if doc_num < 1 or doc_num > num_docs:
                score -= 0.3

        # Check if any citations exist
        if not cited_docs:
            score -= 0.5

        return max(0.0, min(1.0, score))

    def _assess_reasoning_quality(self, response: str) -> float:
        """
        Assess reasoning quality of response.

        TODO: Implement more sophisticated quality assessment.

        Args:
            response: Generated response

        Returns:
            Reasoning quality score (0-1)
        """
        score = 0.7

        # Check length
        if 100 <= len(response) <= 2000:
            score += 0.1

        # Check for structure
        if re.search(r'\d+\.', response) or re.search(r'\*\*', response):
            score += 0.05

        return max(0.0, min(1.0, score))

    # ==========================================================================
    # Unified Quality Scoring
    # ==========================================================================

    def _calculate_quality_score(
        self,
        critique_result: CritiqueResult,
        verification_result: VerificationResult
    ) -> float:
        """
        Calculate unified quality score from critique and verification.

        Args:
            critique_result: Critique assessment
            verification_result: Verification assessment

        Returns:
            Unified quality score (0-1)
        """
        critique_score = self._quality_level_to_score(critique_result.quality_level)
        critique_weight = self.config.weight_critique

        verification_score = verification_result.confidence
        verification_weight = self.config.weight_verification

        # Weighted combination
        unified_score = (critique_score * critique_weight + verification_score * verification_weight)

        return round(unified_score, 2)

    def _quality_level_to_score(self, quality_level: QualityScore) -> float:
        """
        Convert quality level to numeric score.

        Args:
            quality_level: Quality level enum

        Returns:
            Numeric score (0-1)
        """
        mapping = {
            QualityScore.EXCELLENT: 1.0,
            QualityScore.GOOD: 0.8,
            QualityScore.ACCEPTABLE: 0.6,
            QualityScore.POOR: 0.4,
            QualityScore.FAILED: 0.2
        }
        return mapping.get(quality_level, 0.5)

    def _should_regenerate(
        self,
        critique_result: CritiqueResult,
        verification_result: VerificationResult,
        quality_score: float
    ) -> bool:
        """
        Decide if response should be regenerated.

        Args:
            critique_result: Critique assessment
            verification_result: Verification assessment
            quality_score: Unified quality score

        Returns:
            True if regeneration is recommended
        """
        # Check threshold
        if quality_score < self.config.quality_threshold:
            return True

        # Check verification failure
        if not verification_result.is_verified:
            return True

        # Check critique recommendation
        if critique_result.should_regenerate:
            return True

        return False
