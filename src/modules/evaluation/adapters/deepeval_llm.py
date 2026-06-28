"""Adapter that lets DeepEval use the project's LLMPort judge."""

import asyncio
from typing import Any

from src.shared.ports.llm import LLMPort


class DeepEvalLLMAdapter:
    """Lazy DeepEvalBaseLLM wrapper around an async LLMPort.

    The class avoids importing DeepEval at module import time so normal app
    startup still works before dev evaluation dependencies are installed.
    """

    def __new__(cls, llm: LLMPort, model_name: str = "kira-judge"):
        try:
            from deepeval.models import DeepEvalBaseLLM
        except ImportError as exc:
            raise RuntimeError(
                "DeepEval is not installed. Run `uv sync --extra dev` or "
                "`pip install -e '.[dev]'` before running evaluation."
            ) from exc

        class _Adapter(DeepEvalBaseLLM):
            def __init__(self, wrapped_llm: LLMPort, name: str):
                self._llm = wrapped_llm
                self._name = name

            def load_model(self) -> LLMPort:
                return self._llm

            def generate(self, prompt: str, schema: Any | None = None) -> str:
                async def _run() -> str:
                    return await self.a_generate(prompt, schema=schema)

                return asyncio.run(_run())

            async def a_generate(self, prompt: str, schema: Any | None = None) -> str:
                system_guidance = (
                    "LƯU Ý QUAN TRỌNG: Các tài liệu, câu hỏi và câu trả lời đều bằng tiếng Việt. "
                    "Hãy phân tích kỹ ngôn ngữ, ngữ pháp và sắc thái tiếng Việt để đưa ra đánh giá chính xác nhất. "
                    "Mọi phân tích lý do (reason) của bạn nếu có phải được viết bằng tiếng Việt."
                )
                full_prompt = f"{system_guidance}\n\n{prompt}"
                return await self._llm.generate(
                    messages=[{"role": "user", "content": full_prompt}],
                    temperature=0.0,
                    max_tokens=2048,
                )

            def get_model_name(self) -> str:
                return self._name

        return _Adapter(llm, model_name)
