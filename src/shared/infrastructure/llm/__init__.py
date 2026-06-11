"""
LLM Client - Multi-provider LLM abstraction.

Canonical location: src.shared.infrastructure.llm

Provides unified interface for multiple LLM providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Zhipu AI (GLM-4)
- Google (Gemini)

Primary exports:
- LLMClient: Main client class
- chat_async: Async chat function
- chat_async_stream: Async streaming chat function
"""

from src.shared.infrastructure.llm.client import LLMClient, chat_async

__all__ = ["LLMClient", "chat_async"]
