"""LLM-as-a-judge evaluation prompts."""

from src.modules.evaluation.domain.models import EvaluationMetric

MAX_CONTEXTS_IN_PROMPT = 5
CONTEXT_SNIPPET_LENGTH = 500
ANSWER_SNIPPET_LENGTH = 1000


def _format_contexts(contexts: list[str]) -> str:
    """Format retrieved contexts for evaluation prompts."""
    return "\n\n".join(
        f"[Context {i + 1}]: {ctx[:CONTEXT_SNIPPET_LENGTH]}"
        for i, ctx in enumerate(contexts[:MAX_CONTEXTS_IN_PROMPT])
    )


def get_evaluation_prompts(
    metric: EvaluationMetric,
    query: str,
    answer: str,
    contexts: list[str],
) -> tuple[str, str]:
    """Get system and user prompts for an evaluation metric."""
    contexts_text = _format_contexts(contexts)
    answer_text = answer[:ANSWER_SNIPPET_LENGTH]

    if metric == EvaluationMetric.FAITHFULNESS:
        system_prompt = """Bạn là chuyên gia đánh giá chất lượng câu trả lời AI.
Nhiệm vụ: Kiểm tra xem câu trả lời có ĐÚNG với ngữ cảnh được cung cấp không.

Tiêu chí đánh giá:
- 1.0: Câu trả lời hoàn toàn dựa trên ngữ cảnh, không có thông tin sai
- 0.7-0.9: Chủ yếu đúng, có một số chi tiết không chắc chắn
- 0.4-0.6: Một phần đúng, một phần sai hoặc thiếu thông tin
- 0.1-0.3: Chủ yếu sai hoặc không liên quan
- 0.0: Hoàn toàn sai hoặc ảo tưởng

QUAN TRỌNG: Chấm điểm KHẮT KHE - bất kỳ thông tin không có trong ngữ cảnh đều bị trừ điểm."""

        user_prompt = f"""Câu hỏi: {query}

Câu trả lời cần đánh giá:
{answer_text}

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
{answer_text}

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

    else:
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


__all__ = ["get_evaluation_prompts"]
