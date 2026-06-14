"""Small deterministic metrics that complement DeepEval judge metrics."""

from __future__ import annotations


REFUSAL_MARKERS = (
    "không tìm thấy",
    "không có thông tin",
    "không đủ thông tin",
    "không được cung cấp",
    "tài liệu không",
    "i don't know",
    "not enough information",
)


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


def refusal_correctness(answer: str, should_refuse: bool) -> tuple[float, str]:
    """Score whether the model refused when the dataset says it should."""
    normalized = answer.lower()
    refused = any(marker in normalized for marker in REFUSAL_MARKERS)

    if should_refuse and refused:
        return 1.0, "The answer correctly refused due to missing evidence."
    if should_refuse and not refused:
        return 0.0, "The answer should have refused but attempted to answer."
    if not should_refuse and refused:
        return 0.0, "The answer refused even though the sample expects an answer."
    return 1.0, "The answer did not refuse, as expected."
