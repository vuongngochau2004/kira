"""Post-processing layer for LLM streaming responses.

Simple, robust separation of thinking tags from actual content.
"""

import logging
from typing import AsyncIterator

logger = logging.getLogger(__name__)

THINKING_START = "<thinking>"
THINKING_END = "</thinking>"


async def stream_with_thinking_separation(
    raw_stream,
) -> AsyncIterator[dict]:
    """Process raw LLM stream and separate thinking from content.

    Simple state machine:
    1. Before <thinking>: everything is content
    2. Inside <thinking>...</thinking>: everything is thinking
    3. After </thinking>: everything is content

    Args:
        raw_stream: Raw text chunks from LLM

    Yields:
        {"type": "thinking", "text": "..."} or {"type": "content", "text": "..."}
    """
    buffer = ""
    in_thinking = False
    pos = 0  # Current position in buffer

    async for raw_chunk in raw_stream:
        buffer += raw_chunk

        # Process buffer incrementally
        while pos < len(buffer):
            if not in_thinking:
                # Look for <thinking> start
                start_idx = buffer.find(THINKING_START, pos)
                if start_idx == -1:
                    # No <thinking> found - yield everything from pos as content
                    if pos < len(buffer):
                        yield {"type": "content", "text": buffer[pos:]}
                    pos = len(buffer)
                    break
                else:
                    # Yield content before <thinking>
                    if start_idx > pos:
                        yield {"type": "content", "text": buffer[pos:start_idx]}
                    pos = start_idx + len(THINKING_START)
                    in_thinking = True

            else:  # in_thinking is True
                # Look for </thinking> end
                end_idx = buffer.find(THINKING_END, pos)
                if end_idx == -1:
                    # No </thinking> yet - yield thinking content incrementally for streaming
                    # IMPORTANT: Yield current thinking content so UI can show it in real-time
                    if pos < len(buffer):
                        yield {"type": "thinking", "text": buffer[pos:]}
                    pos = len(buffer)
                    break
                else:
                    # Yield thinking content (without the closing tag)
                    yield {"type": "thinking", "text": buffer[pos:end_idx]}
                    pos = end_idx + len(THINKING_END)
                    in_thinking = False

        # Trim processed content from buffer to prevent unbounded growth
        if pos > 1000:  # Keep some buffer for tag detection
            buffer = buffer[pos - 100:]  # Keep last 100 chars
            pos = 100

    # Yield remaining content
    # If still in thinking mode, treat remaining as thinking (LLM forgot closing tag)
    # Otherwise treat as content
    if pos < len(buffer):
        chunk_type = "thinking" if in_thinking else "content"
        yield {"type": chunk_type, "text": buffer[pos:]}


__all__ = ["stream_with_thinking_separation"]
