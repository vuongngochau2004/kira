"""
LLM client adapter for chat module.

Provides a module-local interface to LLM functionality,
delegating to the shared agents.llm module.
"""

from src.modules.chat.infrastructure.llm.client import LLMClientAdapter

# Re-export LLM types for convenience
from src.shared.infrastructure.llm.client import LLMClient, LLMProvider, LLMError, LLMTimeoutError, LLMStreamError

__all__ = [
    "LLMClientAdapter",
    "LLMClient",
    "LLMProvider",
    "LLMError",
    "LLMTimeoutError",
    "LLMStreamError",
]