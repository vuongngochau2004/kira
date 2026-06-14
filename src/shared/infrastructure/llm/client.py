"""LLM provider abstraction for kira-simple.

Provides async interface to multiple LLM providers (GLM, Gemini, OpenAI-compatible)
with streaming and non-streaming modes.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from enum import Enum

from src.config.config import settings

logger = logging.getLogger(__name__)
DEFAULT_LLM_TIMEOUT = 60.0


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    GLM = "glm"
    GEMINI = "gemini"
    OPENAI_COMPATIBLE = "openai_compatible"
    OLLAMA = "ollama"


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""
    pass


class LLMStreamError(LLMError):
    """Raised when LLM streaming fails."""
    pass


def _normalize_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Normalize and validate message format.

    Args:
        messages: List of message dicts with role and content

    Returns:
        Normalized messages list
    """
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in messages
        if msg.get("role") and msg.get("content")
    ]


def _extract_system_message(messages: list[dict[str, str]]) -> tuple[str | None, list[dict[str, str]]]:
    """Extract system message from conversation messages.

    Args:
        messages: List of message dicts

    Returns:
        Tuple of (system_content, conversation_messages)
    """
    system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
    conv_messages = [m for m in messages if m["role"] != "system"]
    return system_msg, conv_messages


async def chat_async(
    messages: list[dict[str, str]],
    provider: LLMProvider | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: float | None = None,
) -> dict[str, str]:
    """Send a chat request asynchronously (non-streaming).

    Args:
        messages: List of message dicts with role and content
        provider: LLM provider (defaults to settings.llm_provider)
        model: Model name (defaults to provider-specific default)
        temperature: Sampling temperature (0.0 - 1.0)
        max_tokens: Max tokens to generate
        timeout: Request timeout in seconds

    Returns:
        Response dict with keys: content, model, provider

    Raises:
        LLMError: If LLM request fails
    """
    provider = provider or LLMProvider(settings.llm_provider)
    timeout = timeout if timeout is not None else DEFAULT_LLM_TIMEOUT

    messages = _normalize_messages(messages)

    logger.debug(
        f"[LLM] provider={provider.value}, model={model or 'default'}, "
        f"temp={temperature}, messages={len(messages)}"
    )

    try:
        if provider == LLMProvider.GLM:
            model = model or settings.glm_model
            return await _chat_glm_async(
                messages, model, temperature, max_tokens, timeout
            )
        elif provider == LLMProvider.GEMINI:
            model = model or settings.gemini_model
            return await _chat_gemini_async(
                messages, model, temperature, max_tokens, timeout
            )
        elif provider == LLMProvider.OLLAMA:
            model = model or settings.ollama_model
            return await _chat_ollama_async(
                messages, model, temperature, max_tokens, timeout
            )
        else:
            model = model or settings.bk_llm_model or "gpt-3.5-turbo"
            return await _chat_openai_async(
                messages, model, temperature, max_tokens, timeout
            )
    except asyncio.TimeoutError as e:
        logger.error(f"[LLM] Timeout after {timeout}s")
        raise LLMTimeoutError(f"LLM request timed out after {timeout}s") from e
    except Exception as e:
        logger.error(f"[LLM] {type(e).__name__}: {e}", exc_info=True)
        raise LLMError(f"LLM request failed: {e}") from e


async def chat_async_stream(
    messages: list[dict[str, str]],
    provider: LLMProvider | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: float | None = None,
) -> AsyncIterator[str]:
    """Stream chat response chunk by chunk.

    Args:
        messages: List of message dicts with role and content
        provider: LLM provider (defaults to settings.llm_provider)
        model: Model name (defaults to provider-specific default)
        temperature: Sampling temperature (0.0 - 1.0)
        max_tokens: Max tokens to generate
        timeout: Request timeout in seconds

    Yields:
        Text chunks as they arrive from LLM

    Raises:
        LLMStreamError: If streaming fails
    """
    provider = provider or LLMProvider(settings.llm_provider)
    timeout = timeout if timeout is not None else DEFAULT_LLM_TIMEOUT

    messages = _normalize_messages(messages)

    logger.debug(
        f"[LLM STREAM] provider={provider.value}, model={model or 'default'}, "
        f"temp={temperature}, messages={len(messages)}"
    )

    try:
        if provider == LLMProvider.GLM:
            model = model or settings.glm_model
            async for chunk in _chat_glm_stream(
                messages, model, temperature, max_tokens, timeout
            ):
                yield chunk
        elif provider == LLMProvider.GEMINI:
            model = model or settings.gemini_model
            async for chunk in _chat_gemini_stream(
                messages, model, temperature, max_tokens, timeout
            ):
                yield chunk
        elif provider == LLMProvider.OLLAMA:
            model = model or settings.ollama_model
            async for chunk in _chat_ollama_stream(
                messages, model, temperature, max_tokens, timeout
            ):
                yield chunk
        else:
            model = model or settings.bk_llm_model or "gpt-3.5-turbo"
            async for chunk in _chat_openai_stream(
                messages, model, temperature, max_tokens, timeout
            ):
                yield chunk
    except asyncio.TimeoutError as e:
        logger.error(f"[LLM STREAM] Timeout after {timeout}s")
        raise LLMTimeoutError(f"LLM stream timed out after {timeout}s") from e
    except Exception as e:
        logger.error(f"[LLM STREAM] {type(e).__name__}: {e}", exc_info=True)
        raise LLMStreamError(f"LLM streaming failed: {e}") from e


async def _chat_glm_async(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> dict[str, str]:
    """Async GLM (Anthropic-compatible) chat.

    Args:
        messages: List of message dicts
        model: Model name
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        timeout: Request timeout

    Returns:
        Response dict with content, model, provider
    """
    import anthropic

    client = anthropic.AsyncAnthropic(
        api_key=settings.glm_api_key,
        base_url=settings.glm_api_url,
        timeout=timeout,
    )

    system_msg, conv_messages = _extract_system_message(messages)

    # Build kwargs dynamically to handle optional system parameter
    # Type ignores: Anthropic SDK has strict types but our dict format works
    kwargs: dict = {
        "model": model,
        "messages": conv_messages,  # type: ignore[arg-type]
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system_msg:
        kwargs["system"] = system_msg

    response = await client.messages.create(**kwargs)

    # Extract text from first text block in response
    content = ""
    for block in response.content:  # type: ignore[attr-defined]
        if hasattr(block, "text"):
            content = block.text
            break

    return {"content": content, "model": model, "provider": LLMProvider.GLM.value}


async def _chat_glm_stream(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> AsyncIterator[str]:
    """Stream GLM (Anthropic-compatible) chat.

    Args:
        messages: List of message dicts
        model: Model name
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        timeout: Request timeout

    Yields:
        Text chunks as they arrive
    """
    import anthropic

    client = anthropic.AsyncAnthropic(
        api_key=settings.glm_api_key,
        base_url=settings.glm_api_url,
        timeout=timeout,
    )

    system_msg, conv_messages = _extract_system_message(messages)

    logger.debug(f"[GLM STREAM] Starting stream with model={model}")

    # Build kwargs dynamically
    # Type ignores: Anthropic SDK has strict types but our dict format works
    kwargs: dict = {
        "model": model,
        "messages": conv_messages,  # type: ignore[arg-type]
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system_msg:
        kwargs["system"] = system_msg

    async with client.messages.stream(**kwargs) as stream:
        async for text in stream.text_stream:
            if text:
                yield text

    logger.debug("[GLM STREAM] Completed")


async def _chat_gemini_async(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> dict[str, str]:
    """Async Gemini chat (wraps sync SDK in thread pool).

    Args:
        messages: List of message dicts
        model: Model name
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        timeout: Request timeout

    Returns:
        Response dict with content, model, provider
    """
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=settings.gemini_api_key)
    system_msg, conv_messages = _extract_system_message(messages)

    # Build contents list with proper format
    contents = []
    for msg in conv_messages:
        if msg["role"] == "user":
            contents.append(genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=msg["content"])]
            ))
        elif msg["role"] == "assistant":
            contents.append(genai_types.Content(
                role="model",
                parts=[genai_types.Part.from_text(text=msg["content"])]
            ))

    # Run in thread pool since Gemini SDK is synchronous
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=contents,  # type: ignore[arg-type]
        config=genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_msg,
        ),
    )

    content = response.text or ""
    return {"content": content, "model": model, "provider": LLMProvider.GEMINI.value}


async def _chat_gemini_stream(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> AsyncIterator[str]:
    """Stream Gemini chat.

    Args:
        messages: List of message dicts
        model: Model name
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        timeout: Request timeout

    Yields:
        Text chunks as they arrive
    """
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=settings.gemini_api_key)
    system_msg, conv_messages = _extract_system_message(messages)

    # Build contents list
    contents = []
    for msg in conv_messages:
        if msg["role"] == "user":
            contents.append(genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=msg["content"])]
            ))
        elif msg["role"] == "assistant":
            contents.append(genai_types.Content(
                role="model",
                parts=[genai_types.Part.from_text(text=msg["content"])]
            ))

    # Run in thread pool since Gemini SDK is synchronous
    def sync_generate():
        return client.models.generate_content_stream(
            model=model,
            contents=contents,  # type: ignore[arg-type]
            config=genai_types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                system_instruction=system_msg,
            ),
        )

    stream = await asyncio.to_thread(sync_generate)

    for chunk in stream:
        if chunk.text:
            yield chunk.text


async def _chat_openai_async(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> dict[str, str]:
    """Async OpenAI-compatible chat (non-streaming).

    Args:
        messages: List of message dicts
        model: Model name
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        timeout: Request timeout

    Returns:
        Response dict with content, model, provider

    Raises:
        httpx.HTTPError: If HTTP request fails
        KeyError: If response format is unexpected
    """
    import httpx

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.bk_api_key or 'not-needed'}",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    url = f"{settings.bk_llm_base_url}/chat/completions"

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    return {
        "content": content,
        "model": model,
        "provider": LLMProvider.OPENAI_COMPATIBLE.value
    }


async def _chat_openai_stream(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> AsyncIterator[str]:
    """Stream OpenAI-compatible chat.

    Args:
        messages: List of message dicts
        model: Model name
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        timeout: Request timeout

    Yields:
        Text chunks as they arrive

    Raises:
        httpx.HTTPError: If HTTP request fails
        json.JSONDecodeError: If SSE data is invalid JSON
    """
    import httpx

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.bk_api_key or 'not-needed'}",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    url = f"{settings.bk_llm_base_url}/chat/completions"

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    if "content" in delta and delta["content"]:
                        yield delta["content"]
                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    logger.debug(f"[OpenAI Stream] Failed to parse chunk: {e}")
                    continue


def _ollama_api_key() -> str:
    """Return the first configured Ollama API key."""
    return settings.ollama_api_keys.split(",", 1)[0].strip()


def _ollama_chat_url() -> str:
    """Return Ollama's OpenAI-compatible chat completions URL."""
    return f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions"


async def _chat_ollama_async(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> dict[str, str]:
    """Async Ollama Cloud chat via its OpenAI-compatible endpoint."""
    import httpx

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_ollama_api_key()}",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(_ollama_chat_url(), json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    return {"content": content, "model": model, "provider": LLMProvider.OLLAMA.value}


async def _chat_ollama_stream(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> AsyncIterator[str]:
    """Stream Ollama Cloud chat via its OpenAI-compatible endpoint."""
    import httpx

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_ollama_api_key()}",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            _ollama_chat_url(),
            json=payload,
            headers=headers,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    if "content" in delta and delta["content"]:
                        yield delta["content"]
                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    logger.debug(f"[Ollama Stream] Failed to parse chunk: {e}")
                    continue


async def chat_async_with_tools(
    messages: list[dict[str, str]],
    tools: list[dict] | None = None,
    provider: LLMProvider | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: float | None = None,
) -> dict[str, any]:
    """Send chat request with tool use support (GLM/Anthropic-compatible only).

    This function enables structured output by leveraging Anthropic's tool use capability.
    The LLM is forced to return responses using the provided tool schema.

    Args:
        messages: List of message dicts with role and content
        tools: Tool definitions for function calling (Anthropic format)
        provider: LLM provider (must be GLM for tool use support)
        model: Model name (defaults to provider-specific default)
        temperature: Sampling temperature (0.0 - 1.0)
        max_tokens: Max tokens to generate
        timeout: Request timeout in seconds

    Returns:
        Response dict with keys:
        - content: Full response content (including tool_use blocks)
        - tool_results: List of parsed tool use results
        - model: Model name used
        - provider: Provider name

    Raises:
        LLMError: If provider doesn't support tool use or request fails
        ValueError: If tools parameter is empty

    Example:
        >>> tools = [{
        ...     "name": "answer_query",
        ...     "input_schema": {"type": "object", "properties": {...}}
        ... }]
        >>> response = await chat_async_with_tools(messages, tools)
        >>> tool_result = response["tool_results"][0]
        >>> has_answer = tool_result["tool_input"]["has_answer"]
    """
    provider = provider or LLMProvider(settings.llm_provider)
    timeout = timeout if timeout is not None else DEFAULT_LLM_TIMEOUT

    if not tools or len(tools) == 0:
        raise ValueError("tools parameter must be non-empty list")

    # Tool use only supported for GLM (Anthropic-compatible)
    if provider != LLMProvider.GLM:
        raise LLMError(
            f"Tool use only supported for GLM (Anthropic-compatible) provider. "
            f"Got: {provider.value}"
        )

    messages = _normalize_messages(messages)

    logger.debug(
        f"[LLM TOOLS] provider={provider.value}, model={model or 'default'}, "
        f"temp={temperature}, tools={len(tools)}, messages={len(messages)}"
    )

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(
            api_key=settings.glm_api_key,
            base_url=settings.glm_api_url,
            timeout=timeout,
        )

        system_msg, conv_messages = _extract_system_message(messages)

        # Build kwargs dynamically
        kwargs: dict = {
            "model": model or settings.glm_model,
            "messages": conv_messages,  # type: ignore[arg-type]
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": tools,  # ✅ Add tools here for structured output
        }
        if system_msg:
            kwargs["system"] = system_msg

        response = await client.messages.create(**kwargs)

        # ✅ Parse tool_use blocks from response
        tool_results = []
        for block in response.content:  # type: ignore[attr-defined]
            if hasattr(block, "type") and block.type == "tool_use":
                tool_results.append({
                    "tool_name": block.name,
                    "tool_input": block.input,
                    "tool_id": block.id
                })

        if not tool_results:
            logger.warning(
                f"[LLM TOOLS] No tool_use blocks found in response. "
                f"Response type: {type(response.content)}"
            )

        logger.debug(
            f"[LLM TOOLS] Completed. Tool results: {len(tool_results)}, "
            f"Tools used: {[r['tool_name'] for r in tool_results]}"
        )

        return {
            "content": response.content,  # Full content for reference
            "tool_results": tool_results,  # ✅ Structured data here
            "model": model or settings.glm_model,
            "provider": provider.value,
            "stop_reason": getattr(response, "stop_reason", None)
        }

    except asyncio.TimeoutError as e:
        logger.error(f"[LLM TOOLS] Timeout after {timeout}s")
        raise LLMTimeoutError(f"LLM tool use request timed out after {timeout}s") from e
    except Exception as e:
        logger.error(f"[LLM TOOLS] {type(e).__name__}: {e}", exc_info=True)
        raise LLMError(f"LLM tool use request failed: {e}") from e


__all__ = [
    "chat_async",
    "chat_async_stream",
    "chat_async_with_tools",  # NEW
    "LLMClient",
    "LLMProvider",
    "LLMError",
    "LLMTimeoutError",
    "LLMStreamError",
]


class LLMClient:
    """Class-based interface for LLM calls with default parameters.

    Useful for dependency injection, testing, and when you need multiple
    LLM clients with different configurations.

    Example:
        ```python
        client = LLMClient(provider=LLMProvider.GLM, model="glm-4.5")
        response = await client.chat_async(messages)
        ```
    """

    def __init__(
        self,
        provider: LLMProvider | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: float | None = None,
    ):
        """Initialize LLM client with default parameters.

        Args:
            provider: LLM provider (defaults to settings.llm_provider)
            model: Model name (defaults to provider-specific default)
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Max tokens to generate
            timeout: Request timeout in seconds
        """
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    async def chat_async(
        self,
        messages: list[dict[str, str]],
        provider: LLMProvider | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> dict[str, str]:
        """Send a chat request asynchronously.

        Args:
            messages: List of message dicts with role and content
            provider: Override default provider
            model: Override default model
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            timeout: Override default timeout

        Returns:
            Response dict with content, model, provider

        Raises:
            LLMError: If LLM request fails
        """
        return await chat_async(
            messages=messages,
            provider=provider or self.provider,
            model=model or self.model,
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
            timeout=timeout if timeout is not None else self.timeout,
        )

    async def chat_async_stream(
        self,
        messages: list[dict[str, str]],
        provider: LLMProvider | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat response chunk by chunk.

        Args:
            messages: List of message dicts with role and content
            provider: Override default provider
            model: Override default model
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            timeout: Override default timeout

        Yields:
            Text chunks as they arrive from LLM

        Raises:
            LLMStreamError: If streaming fails
        """
        stream = chat_async_stream(
            messages=messages,
            provider=provider or self.provider,
            model=model or self.model,
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
            timeout=timeout if timeout is not None else self.timeout,
        )
        async for chunk in stream:
            yield chunk
