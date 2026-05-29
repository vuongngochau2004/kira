"""LLM provider abstraction for kira-simple."""

import sys
import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.config import settings

logger = logging.getLogger(__name__)
DEFAULT_LLM_TIMEOUT = 60.0


async def chat_async(
    messages: list[dict],
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: float | None = None,
    stream_callback = None,
) -> dict:
    """Send a chat request asynchronously (non-streaming).

    Args:
        messages: List of message dicts with role and content
        provider: LLM provider (glm, gemini, openai)
        model: Model name
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        timeout: Request timeout
        stream_callback: Optional callback for streaming (DEPRECATED - use chat_async_stream)

    Returns:
        Response dict with content, model, provider
    """
    provider = provider or settings.llm_provider
    timeout = timeout if timeout is not None else DEFAULT_LLM_TIMEOUT

    logger.debug(f"[LLM] provider={provider}, model={model or 'default'}, temp={temperature}")

    try:
        if provider == "glm":
            model = model or settings.glm_model
            return await _chat_glm_async(
                messages, model, temperature, max_tokens, timeout, stream_callback
            )
        if provider == "gemini":
            model = model or settings.gemini_model
            return await asyncio.to_thread(
                _chat_gemini_sync,
                messages, model, temperature, max_tokens, timeout
            )

        model = model or settings.bk_llm_model or "gpt-3.5-turbo"
        return await _chat_openai_async(
            messages, model, temperature, max_tokens, timeout, stream_callback
        )
    except Exception as e:
        logger.error(f"[LLM] Error: {type(e).__name__}: {e}")
        raise


async def chat_async_stream(
    messages: list[dict],
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: float | None = None,
) -> AsyncIterator[str]:
    """Stream chat response chunk by chunk.

    Args:
        messages: List of message dicts with role and content
        provider: LLM provider (glm, gemini, openai)
        model: Model name
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        timeout: Request timeout

    Yields:
        Text chunks as they arrive from LLM

    Raises:
        Exception: If LLM provider fails
    """
    provider = provider or settings.llm_provider
    timeout = timeout if timeout is not None else DEFAULT_LLM_TIMEOUT

    logger.debug(f"[LLM STREAM] provider={provider}, model={model or 'default'}, temp={temperature}")

    try:
        if provider == "glm":
            model = model or settings.glm_model
            async for chunk in _chat_glm_stream(
                messages, model, temperature, max_tokens, timeout
            ):
                yield chunk
        elif provider == "gemini":
            model = model or settings.gemini_model
            async for chunk in _chat_gemini_stream(
                messages, model, temperature, max_tokens, timeout
            ):
                yield chunk
        else:
            model = model or settings.bk_llm_model or "gpt-3.5-turbo"
            async for chunk in _chat_openai_stream(
                messages, model, temperature, max_tokens, timeout
            ):
                yield chunk
    except Exception as e:
        logger.error(f"[LLM STREAM] Error: {type(e).__name__}: {e}")
        raise


async def _chat_glm_async(
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
    stream_callback = None,
) -> dict:
    """Async GLM (Anthropic-compatible) chat."""
    import anthropic

    client = anthropic.AsyncAnthropic(
        api_key=settings.glm_api_key,
        base_url=settings.glm_api_url,
        timeout=timeout,
    )

    system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
    conv_messages = [m for m in messages if m["role"] != "system"]

    if not stream_callback:
        response = await client.messages.create(
            model=model,
            system=system_msg,
            messages=conv_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.content[0].text if response.content else ""
        return {"content": content, "model": model, "provider": "glm"}

    full_content = []
    async with client.messages.stream(
        model=model,
        system=system_msg,
        messages=conv_messages,
        temperature=temperature,
        max_tokens=max_tokens,
    ) as stream:
        async for text in stream.text_stream:
            if text:
                full_content.append(text)
                try:
                    stream_callback(text)
                except Exception as cb_err:
                    logger.error(f"[LLM] Callback error: {cb_err}")

    return {"content": "".join(full_content), "model": model, "provider": "glm"}


async def _chat_glm_stream(
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> AsyncIterator[str]:
    """Stream GLM (Anthropic-compatible) chat."""
    import anthropic

    client = anthropic.AsyncAnthropic(
        api_key=settings.glm_api_key,
        base_url=settings.glm_api_url,
        timeout=timeout,
    )

    system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
    conv_messages = [m for m in messages if m["role"] != "system"]

    async with client.messages.stream(
        model=model,
        system=system_msg,
        messages=conv_messages,
        temperature=temperature,
        max_tokens=max_tokens,
    ) as stream:
        async for text in stream.text_stream:
            if text:
                yield text


def _chat_gemini_sync(
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> dict:
    """Sync Gemini chat."""
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=settings.gemini_api_key)
    system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)

    contents = []
    for msg in messages:
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

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_msg,
        ),
    )

    content = response.text or ""
    return {"content": content, "model": model, "provider": "gemini"}


async def _chat_gemini_stream(
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> AsyncIterator[str]:
    """Stream Gemini chat."""
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=settings.gemini_api_key)
    system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)

    contents = []
    for msg in messages:
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
            contents=contents,
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
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
    stream_callback = None,
) -> dict:
    """Async OpenAI-compatible chat."""
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
    if stream_callback:
        payload["stream"] = True

    url = f"{settings.bk_llm_base_url}/chat/completions"

    async with httpx.AsyncClient(timeout=timeout) as client:
        if not stream_callback:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return {"content": content, "model": model, "provider": "openai_compatible"}

        full_content = []
        async with client.stream("POST", url, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = __import__("json").loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    if "content" in delta and delta["content"]:
                        chunk = delta["content"]
                        full_content.append(chunk)
                        if asyncio.iscoroutinefunction(stream_callback):
                            await stream_callback(chunk)
                        else:
                            stream_callback(chunk)
                except Exception:
                    pass

        return {"content": "".join(full_content), "model": model, "provider": "openai_compatible"}


async def _chat_openai_stream(
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> AsyncIterator[str]:
    """Stream OpenAI-compatible chat."""
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
                    data = __import__("json").loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    if "content" in delta and delta["content"]:
                        yield delta["content"]
                except Exception:
                    pass


__all__ = ["chat_async", "chat_async_stream"]
