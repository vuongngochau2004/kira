"""Small deterministic metrics that complement DeepEval judge metrics."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.ports.llm import LLMPort


REFUSAL_MARKERS = (
    "không tìm thấy",
    "không có thông tin",
    "không đủ thông tin",
    "không được cung cấp",
    "tài liệu không",
    "i don't know",
    "not enough information",
)


async def refusal_correctness(
    answer: str,
    should_refuse: bool,
    llm: LLMPort | None = None,
) -> tuple[float, str]:
    """Score whether the model refused when the dataset says it should."""
    normalized = answer.lower()
    refused = any(marker in normalized for marker in REFUSAL_MARKERS)

    # 1. First, check the fast deterministic heuristic.
    # If the heuristic matches should_refuse, we can trust it and save API latency/cost.
    if should_refuse == refused:
        reason = (
            "The answer correctly refused due to missing evidence (heuristic match)."
            if should_refuse
            else "The answer did not refuse, as expected (heuristic match)."
        )
        return 1.0, reason

    # 2. If there is a mismatch, use the LLM judge to classify refusal semantically.
    if llm is not None:
        try:
            prompt = f"""Bạn là giám khảo đánh giá hệ thống RAG tiếng Việt.
Nhiệm vụ của bạn là xác định xem phản hồi của trợ lý có phải là một lời TỪ CHỐI TRẢ LỜI do không tìm thấy thông tin hoặc thiếu tài liệu hay không.

PHẢN HỒI CỦA TRỢ LÝ:
"{answer}"

Hãy trả về duy nhất một đối tượng JSON có định dạng sau:
{{
  "is_refusal": true/false,
  "reason": "Giải thích ngắn gọn lý do tại sao phản hồi này là từ chối hay không"
}}
Không thêm bất kỳ văn bản nào khác ngoài JSON.
"""
            raw_response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=300,
            )

            text = raw_response.strip()
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", text, flags=re.DOTALL)
                parsed = json.loads(match.group(0)) if match else {}

            is_refusal = bool(parsed.get("is_refusal", False))
            llm_reason = parsed.get("reason", "")

            if should_refuse and is_refusal:
                return 1.0, f"LLM Judge: Phản hồi từ chối chính xác. Lý do: {llm_reason}"
            if not should_refuse and not is_refusal:
                return 1.0, f"LLM Judge: Phản hồi không từ chối, đúng kỳ vọng. Lý do: {llm_reason}"
            if should_refuse and not is_refusal:
                return 0.0, f"LLM Judge: Đáng lẽ phải từ chối nhưng mô hình đã cố trả lời. Lý do: {llm_reason}"
            if not should_refuse and is_refusal:
                return 0.0, f"LLM Judge: Đáng lẽ phải trả lời nhưng mô hình lại từ chối. Lý do: {llm_reason}"

        except Exception as exc:
            # Fall back to heuristic result below if LLM judge fails
            pass

    # Heuristic fallback
    if should_refuse and refused:
        return 1.0, "The answer correctly refused due to missing evidence."
    if should_refuse and not refused:
        return 0.0, "The answer should have refused but attempted to answer."
    if not should_refuse and refused:
        return 0.0, "The answer refused even though the sample expects an answer."
    return 1.0, "The answer did not refuse, as expected."


def hit_rate_at_k(expected: list[str], retrieved: list[str], k: int) -> tuple[float, str]:
    """Score whether any expected context appears in the first k retrieved contexts."""
    expected_set = _identifiers(expected)
    if not expected_set:
        return 0.0, "No expected contexts were defined for this sample."
    top_k = _identifiers(retrieved[:k])
    matched = expected_set.intersection(top_k)
    score = 1.0 if matched else 0.0
    return score, f"Hit@{k}: matched {len(matched)}/{len(expected_set)} expected contexts."


def mean_reciprocal_rank(expected: list[str], retrieved: list[str]) -> tuple[float, str]:
    """Score the reciprocal rank of the first expected retrieved context."""
    expected_set = _identifiers(expected)
    if not expected_set:
        return 0.0, "No expected contexts were defined for this sample."
    for rank, identifier in enumerate(retrieved, start=1):
        if identifier.strip() in expected_set:
            score = 1.0 / rank
            return score, f"First expected context found at rank {rank}."
    return 0.0, "No expected context was retrieved."


def recall_at_k(expected: list[str], retrieved: list[str], k: int) -> tuple[float, str]:
    """Score the share of expected contexts returned in the first k results."""
    expected_set = _identifiers(expected)
    if not expected_set:
        return 0.0, "No expected contexts were defined for this sample."
    matched = expected_set.intersection(_identifiers(retrieved[:k]))
    score = len(matched) / len(expected_set)
    return score, f"Recall@{k}: matched {len(matched)}/{len(expected_set)} expected contexts."


def citation_accuracy(expected: list[str], actual: list[str]) -> tuple[float, str]:
    """Score whether expected citation/document identifiers were returned."""
    expected_set = {item.strip() for item in expected if item and item.strip()}
    actual_set = {item.strip() for item in actual if item and item.strip()}

    if not expected_set:
        return 1.0, "No expected citations were defined for this sample."
    if not actual_set:
        return 0.0, "The answer returned no citations."

    matched = expected_set.intersection(actual_set)
    score = len(matched) / len(expected_set)
    return score, f"Matched {len(matched)}/{len(expected_set)} expected citations."


def _clean_text_to_words(text: str) -> list[str]:
    """Clean text by keeping alphanumeric characters and converting to lowercase."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return [w for w in text.split() if w]


def is_semantic_match(retrieved: str, expected: str, threshold: float = 0.65) -> bool:
    """Determine if a retrieved context chunk matches an expected context chunk."""
    retrieved_lower = retrieved.lower()
    expected_lower = expected.lower()
    if expected_lower in retrieved_lower or retrieved_lower in expected_lower:
        return True

    r_words = _clean_text_to_words(retrieved)
    e_words = _clean_text_to_words(expected)
    if not r_words or not e_words:
        return False

    r_set = set(r_words)
    e_set = set(e_words)

    intersection = r_set.intersection(e_set)
    containment = len(intersection) / len(e_set)
    if containment >= threshold:
        return True

    return False


def hit_rate_at_k_text(
    expected_texts: list[str], retrieved_texts: list[str], k: int
) -> tuple[float, str]:
    """Score whether any expected context content matches top-k retrieved contexts."""
    if not expected_texts:
        return 0.0, "No expected contexts were defined for this sample."

    matched_count = 0
    for r_text in retrieved_texts[:k]:
        for e_text in expected_texts:
            if is_semantic_match(r_text, e_text):
                matched_count += 1
                break

    score = 1.0 if matched_count > 0 else 0.0
    return (
        score,
        f"Hit@{k}: matched {matched_count}/{len(expected_texts)} expected contexts via content match.",
    )


def mean_reciprocal_rank_text(
    expected_texts: list[str], retrieved_texts: list[str]
) -> tuple[float, str]:
    """Score the reciprocal rank of the first expected context matched in retrieved contexts."""
    if not expected_texts:
        return 0.0, "No expected contexts were defined for this sample."

    for rank, r_text in enumerate(retrieved_texts, start=1):
        for e_text in expected_texts:
            if is_semantic_match(r_text, e_text):
                score = 1.0 / rank
                return score, f"First expected context matched via content at rank {rank}."

    return 0.0, "No expected context was retrieved."


def recall_at_k_text(
    expected_texts: list[str], retrieved_texts: list[str], k: int
) -> tuple[float, str]:
    """Score the share of expected contexts matched in the first k retrieved contexts."""
    if not expected_texts:
        return 0.0, "No expected contexts were defined for this sample."

    matched_indices = set()
    for r_text in retrieved_texts[:k]:
        for idx, e_text in enumerate(expected_texts):
            if is_semantic_match(r_text, e_text):
                matched_indices.add(idx)

    score = len(matched_indices) / len(expected_texts)
    return (
        score,
        f"Recall@{k}: matched {len(matched_indices)}/{len(expected_texts)} expected contexts via content match.",
    )


def _identifiers(values: list[str]) -> set[str]:
    """Normalize non-empty context identifiers for deterministic comparisons."""
    return {value.strip() for value in values if value and value.strip()}

