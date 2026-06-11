"""RAGAS evaluation service using LLM-as-a-judge."""

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from src.shared.infrastructure.llm.client import LLMProvider, chat_async
from src.models.evaluation import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluationResult,
    EvaluationMetric,
    BatchEvaluationRequest,
    BatchEvaluationResponse,
)
from src.config.config import settings

logger = logging.getLogger(__name__)


# Constants for cache key generation
CACHE_HASH_PREFIX_LENGTH = 8  # 64 bits (sufficient for collision avoidance)
MAX_CONTEXTS_IN_PROMPT = 5  # Maximum contexts to include in evaluation prompt
CONTEXT_SNIPPET_LENGTH = 500  # Truncate contexts for token efficiency
ANSWER_SNIPPET_LENGTH = 1000  # Truncate answers for token efficiency
QUERY_SNIPPET_LENGTH = 100  # Truncate queries for cache key


class EvaluationError(Exception):
    """Base exception for evaluation errors."""
    pass


class EvaluationTimeoutError(EvaluationError):
    """Raised when LLM evaluation times out."""
    pass


class EvaluationParseError(EvaluationError):
    """Raised when LLM response cannot be parsed."""
    pass


class LLMProviderError(EvaluationError):
    """Raised when LLM provider call fails."""
    pass


class RAGASEvaluationService:
    """Service for RAGAS-style evaluation using LLM-as-a-judge.

    Uses existing LLM infrastructure to evaluate RAG outputs
    on faithfulness, answer relevancy, context precision, and context recall.
    """

    def __init__(
        self,
        cache_enabled: bool | None = None,
        timeout_seconds: int | None = None,
    ):
        """Initialize evaluation service.

        Args:
            cache_enabled: Enable result caching
            timeout_seconds: Timeout per evaluation
        """
        self.cache_enabled = cache_enabled if cache_enabled is not None else settings.ragas_cache_enabled
        self.timeout_seconds = timeout_seconds or settings.ragas_timeout_seconds
        self._cache: dict[str, EvaluationResult] = {}

    async def evaluate(
        self,
        request: EvaluationRequest,
    ) -> EvaluationResponse:
        """Evaluate a single RAG output.

        Args:
            request: Evaluation request with query, answer, contexts

        Returns:
            EvaluationResponse with metric scores
        """
        evaluation_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(f"[RAGAS EVAL] Starting evaluation {evaluation_id}")

        results = []
        for metric in request.metrics:
            try:
                result = await self._evaluate_metric(
                    metric=metric,
                    query=request.query,
                    answer=request.answer,
                    contexts=request.contexts,
                )
                results.append(result)
            except EvaluationTimeoutError as e:
                # Expected timeout errors - log and continue with error result
                logger.warning(f"[RAGAS EVAL] Timeout evaluating {metric.value}: {e}")
                results.append(EvaluationResult(
                    metric=metric,
                    score=0.0,
                    error=f"Evaluation timeout: {e}",
                ))
            except EvaluationParseError as e:
                # Parse errors - LLM returned unparseable response
                logger.warning(f"[RAGAS EVAL] Parse error for {metric.value}: {e}")
                results.append(EvaluationResult(
                    metric=metric,
                    score=0.0,
                    error=f"Parse error: {e}",
                ))
            except LLMProviderError as e:
                # LLM provider errors - these are usually transient
                logger.error(f"[RAGAS EVAL] LLM provider error for {metric.value}: {e}")
                results.append(EvaluationResult(
                    metric=metric,
                    score=0.0,
                    error=f"LLM error: {e}",
                ))
            except Exception as e:
                # Unexpected errors - should not happen in production
                logger.exception(f"[RAGAS EVAL] Unexpected error evaluating {metric.value}")
                raise EvaluationError(f"Unexpected error in {metric.value}: {e}") from e

        duration = time.time() - start_time
        overall_score = self._calculate_overall_score(results)

        logger.info(
            f"[RAGAS EVAL] Completed {evaluation_id} "
            f"in {duration:.2f}s, overall={overall_score:.2f}"
        )

        return EvaluationResponse(
            evaluation_id=evaluation_id,
            query=request.query,
            results=results,
            overall_score=overall_score,
            evaluated_at=datetime.utcnow(),
            evaluation_duration_seconds=duration,
            llm_provider=settings.ragas_llm_provider or settings.llm_provider,
            llm_model=settings.glm_model if settings.ragas_llm_provider == "glm" else "unknown",
        )

    async def evaluate_batch(
        self,
        request: BatchEvaluationRequest,
    ) -> BatchEvaluationResponse:
        """Evaluate multiple RAG outputs in batch.

        Args:
            request: Batch evaluation request

        Returns:
            BatchEvaluationResponse with aggregated results
        """
        batch_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(f"[RAGAS BATCH] Starting batch {batch_id} with {len(request.queries)} queries")

        # Process queries concurrently with semaphore
        semaphore = asyncio.Semaphore(request.concurrent_evaluations)

        async def evaluate_single(query_data: dict) -> EvaluationResponse | None:
            async with semaphore:
                try:
                    eval_request = EvaluationRequest(
                        query=query_data["query"],
                        answer=query_data["answer"],
                        contexts=query_data["contexts"],
                        metrics=request.metrics,
                    )
                    return await self.evaluate(eval_request)
                except Exception as e:
                    logger.error(f"[RAGAS BATCH] Failed to evaluate query: {e}")
                    return None

        tasks = [evaluate_single(q) for q in request.queries]
        raw_results = await asyncio.gather(*tasks)

        successful = [r for r in raw_results if r is not None]
        failed = len(raw_results) - len(successful)

        aggregated = self._aggregate_scores(successful)

        duration = time.time() - start_time

        logger.info(
            f"[RAGAS BATCH] Completed batch {batch_id}: "
            f"{len(successful)} successful, {failed} failed, {duration:.2f}s"
        )

        return BatchEvaluationResponse(
            batch_id=batch_id,
            total_queries=len(request.queries),
            successful_evaluations=len(successful),
            failed_evaluations=failed,
            results=successful,
            aggregated_scores=aggregated,
            started_at=datetime.fromtimestamp(start_time),
            completed_at=datetime.utcnow(),
            total_duration_seconds=duration,
        )

    async def _evaluate_metric(
        self,
        metric: EvaluationMetric,
        query: str,
        answer: str,
        contexts: list[str],
    ) -> EvaluationResult:
        """Evaluate a single metric.

        Args:
            metric: Metric to evaluate
            query: Original query
            answer: Generated answer
            contexts: Retrieved contexts

        Returns:
            EvaluationResult with score and reasoning

        Raises:
            EvaluationTimeoutError: If LLM call times out
            EvaluationParseError: If LLM response cannot be parsed
            LLMProviderError: If LLM provider call fails
        """
        # Check cache
        cache_key = self._get_cache_key(metric, query, answer, contexts)
        if self.cache_enabled and cache_key in self._cache:
            logger.debug(f"[RAGAS EVAL] Cache hit for {metric.value}")
            return self._cache[cache_key]

        # Get evaluation prompt for metric
        system_prompt, user_prompt = self._get_evaluation_prompts(
            metric, query, answer, contexts
        )

        # Call LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            provider = LLMProvider(settings.ragas_llm_provider or settings.llm_provider)
            response = await chat_async(
                messages=messages,
                provider=provider,
                model=settings.glm_model if provider == LLMProvider.GLM else None,
                temperature=0.1,  # Low temperature for consistent evaluation
                max_tokens=512,
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError as e:
            raise EvaluationTimeoutError(f"LLM call timed out after {self.timeout_seconds}s") from e
        except Exception as e:
            raise LLMProviderError(f"LLM provider call failed: {e}") from e

        # Parse score from response
        try:
            score, reasoning = self._parse_evaluation_response(
                response["content"], metric
            )
        except Exception as e:
            raise EvaluationParseError(f"Failed to parse LLM response: {e}") from e

        result = EvaluationResult(
            metric=metric,
            score=score,
            reasoning=reasoning,
        )

        # Cache result
        if self.cache_enabled:
            self._cache[cache_key] = result

        return result

    def _get_evaluation_prompts(
        self,
        metric: EvaluationMetric,
        query: str,
        answer: str,
        contexts: list[str],
    ) -> tuple[str, str]:
        """Get evaluation prompts for metric (Vietnamese localized)."""

        contexts_text = "\n\n".join([
            f"[Context {i+1}]: {ctx[:CONTEXT_SNIPPET_LENGTH]}"  # Truncate for token efficiency
            for i, ctx in enumerate(contexts[:MAX_CONTEXTS_IN_PROMPT])  # Max N contexts
        ])

        if metric == EvaluationMetric.FAITHFULNESS:
            system_prompt = """Bạn là chuyên gia đánh giá chất lượng câu trả lời AI.
Nhiệm vụ: Kiểm tra xem câu trả lời có ĐÚNG với ngữ cảnh được cung cấp không.

Tiêu chí đánh giá:
- 1.0: Câu trả lời hoàn toàn dựa trên ngữ cảnh, không có thông tin sai
- 0.7-0.9: Chủ yếu đúng, có một số chi tiết không chắc chắn
- 0.4-0.6: Một phần đúng, một phần sai hoặc thiếu thông tin
- 0.1-0.3: Chủ yếu sai hoặc không liên quan
- 0.0: Hoàn toàn sai hoặc ảo tưởng

QUAN TRỌNG: Chấm điểm KHÁT KHE - bất kỳ thông tin không có trong ngữ cảnh đều bị trừ điểm."""

            user_prompt = f"""Câu hỏi: {query}

Câu trả lời cần đánh giá:
{answer[:ANSWER_SNIPPET_LENGTH]}

Ngữ cảnh:
{contexts_text}

Trả về ĐÚNG định dạng JSON này (không có text khác):
{{
  "score": <điểm số 0-1>,
  "reasoning": "<giải thích ngắn gọn vì sao chấm điểm này>"
}}"""

        elif metric == EvaluationMetric.ANSWER_RELEVANCY:
            system_prompt = """Bạn là chuyên gia đánh giá chất lượng câu trả lời AI.
Nhiệm vụ: Kiểm tra xem câu trả lời có TRẢ LỜI ĐƯỢC câu hỏi không.

Tiêu chí đánh giá:
- 1.0: Trả lời đầy đủ và chính xác câu hỏi
- 0.7-0.9: Trả lời tốt nhưng thiếu một số chi tiết
- 0.4-0.6: Trả lời một phần hoặc lan man
- 0.1-0.3: Trả lời không đúng trọng tâm hoặc quá ngắn
- 0.0: Không trả lời được câu hỏi"""

            user_prompt = f"""Câu hỏi: {query}

Câu trả lời cần đánh giá:
{answer[:ANSWER_SNIPPET_LENGTH]}

Trả về ĐÚNG định dạng JSON này:
{{
  "score": <điểm số 0-1>,
  "reasoning": "<giải thích ngắn gọn>"
}}"""

        elif metric == EvaluationMetric.CONTEXT_PRECISION:
            system_prompt = """Bạn là chuyên gia đánh giá chất lượng retrieval.
Nhiệm vụ: Kiểm tra xem các ngữ cảnh được lấy về có LIÊN QUAN đến câu hỏi không.

Tiêu chí đánh giá:
- 1.0: Tất cả ngữ cảnh đều rất liên quan
- 0.7-0.9: Đa số ngữ cảnh liên quan
- 0.4-0.6: Một nửa số ngữ cảnh liên quan
- 0.1-0.3: Ít ngữ cảnh liên quan
- 0.0: Không có ngữ cảnh nào liên quan"""

            user_prompt = f"""Câu hỏi: {query}

Các ngữ cảnh được lấy về:
{contexts_text}

Trả về ĐÚNG định dạng JSON này:
{{
  "score": <điểm số 0-1>,
  "reasoning": "<giải thích ngắn gọn>"
}}"""

        else:  # CONTEXT_RECALL
            system_prompt = """Bạn là chuyên gia đánh giá chất lượng retrieval.
Nhiệm vụ: Kiểm tra xem có BỎ LỠ ngữ cảnh quan trọng nào không.

Tiêu chí đánh giá:
- 1.0: Không bỏ sót thông tin quan trọng
- 0.7-0.9: Bỏ sót một số chi tiết nhỏ
- 0.4-0.6: Bỏ sót một số thông tin quan trọng
- 0.1-0.3: Bỏ sót nhiều thông tin quan trọng
- 0.0: Bỏ sót hầu hết thông tin quan trọng"""

            user_prompt = f"""Câu hỏi: {query}

Các ngữ cảnh được lấy về:
{contexts_text}

Trả về ĐÚNG định dạng JSON này:
{{
  "score": <điểm số 0-1>,
  "reasoning": "<giải thích ngắn gọn>"
}}"""

        return system_prompt, user_prompt

    def _parse_evaluation_response(
        self,
        response: str,
        metric: EvaluationMetric,
    ) -> tuple[float, str | None]:
        """Parse score from LLM response."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                score = float(data.get("score", 0.5))
                reasoning = data.get("reasoning")
                return max(0.0, min(1.0, score)), reasoning
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.debug(f"[RAGAS EVAL] Failed to parse JSON: {e}")

        # Fallback: extract score from text
        score_match = re.search(r'score["\']?\s*[:=]\s*([0-9.]+)', response, re.IGNORECASE)
        if score_match:
            score = float(score_match.group(1))
            return max(0.0, min(1.0, score)), None

        # Default score if parsing fails
        logger.warning(f"[RAGAS EVAL] Could not parse score, defaulting to 0.5")
        return 0.5, None

    def _get_cache_key(
        self,
        metric: EvaluationMetric,
        query: str,
        answer: str,
        contexts: list[str],
    ) -> str:
        """Generate cache key for evaluation.

        Uses MD5 hash of contexts (truncated) and query/answer snippets
        to create a unique cache key. 64-bit prefix provides sufficient
        collision avoidance for cache usage.
        """
        contexts_hash = hashlib.md5(
            "\n".join(contexts).encode()
        ).hexdigest()[:CACHE_HASH_PREFIX_LENGTH]

        key_string = f"{metric.value}:{query[:QUERY_SNIPPET_LENGTH]}:{answer[:QUERY_SNIPPET_LENGTH]}:{contexts_hash}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _calculate_overall_score(self, results: list[EvaluationResult]) -> float:
        """Calculate overall score from metric results."""
        if not results:
            return 0.0

        valid_scores = [r.score for r in results if r.error is None]
        if not valid_scores:
            return 0.0

        return sum(valid_scores) / len(valid_scores)

    def _aggregate_scores(self, evaluations: list[EvaluationResponse]) -> dict[str, float]:
        """Aggregate scores across batch evaluations."""
        if not evaluations:
            return {}

        metric_scores: dict[str, list[float]] = {}

        for eval_response in evaluations:
            for result in eval_response.results:
                if result.error is None:
                    metric_scores.setdefault(result.metric.value, []).append(result.score)

        aggregated = {}
        for metric, scores in metric_scores.items():
            aggregated[metric] = sum(scores) / len(scores)

        # Add overall average
        if aggregated:
            aggregated["overall"] = sum(aggregated.values()) / len(aggregated)

        return aggregated

    def clear_cache(self) -> int:
        """Clear evaluation cache.

        Returns:
            Number of cache entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        return count


# Singleton instance
_evaluation_service: RAGASEvaluationService | None = None


def get_evaluation_service() -> RAGASEvaluationService:
    """Get or create evaluation service singleton."""
    global _evaluation_service
    if _evaluation_service is None:
        _evaluation_service = RAGASEvaluationService()
    return _evaluation_service


__all__ = [
    "RAGASEvaluationService",
    "get_evaluation_service",
    "EvaluationError",
    "EvaluationTimeoutError",
    "EvaluationParseError",
    "LLMProviderError",
]
