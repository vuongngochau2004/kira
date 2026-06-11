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

    async for raw_chunk in raw_stream:
        buffer += raw_chunk

        while True:
            if not in_thinking:
                start_idx = buffer.find(THINKING_START)
                if start_idx != -1:
                    content_before = buffer[:start_idx]
                    if content_before:
                        yield {"type": "content", "text": content_before}
                    buffer = buffer[start_idx + len(THINKING_START):]
                    in_thinking = True
                    continue
                else:
                    # Check for partial prefix of "<thinking>" at the end of the buffer
                    partial_match_len = 0
                    for i in range(1, len(THINKING_START)):
                        prefix = THINKING_START[:i]
                        if buffer.endswith(prefix):
                            partial_match_len = i
                    
                    if partial_match_len > 0:
                        content_to_yield = buffer[:-partial_match_len]
                        buffer = buffer[-partial_match_len:]
                    else:
                        content_to_yield = buffer
                        buffer = ""
                    
                    if content_to_yield:
                        yield {"type": "content", "text": content_to_yield}
                    break
            else:
                end_idx = buffer.find(THINKING_END)
                if end_idx != -1:
                    thinking_content = buffer[:end_idx]
                    if thinking_content:
                        yield {"type": "thinking", "text": thinking_content}
                    buffer = buffer[end_idx + len(THINKING_END):]
                    in_thinking = False
                    continue
                else:
                    # Check for partial prefix of "</thinking>" at the end of the buffer
                    partial_match_len = 0
                    for i in range(1, len(THINKING_END)):
                        prefix = THINKING_END[:i]
                        if buffer.endswith(prefix):
                            partial_match_len = i
                    
                    if partial_match_len > 0:
                        thinking_to_yield = buffer[:-partial_match_len]
                        buffer = buffer[-partial_match_len:]
                    else:
                        thinking_to_yield = buffer
                        buffer = ""
                    
                    if thinking_to_yield:
                        yield {"type": "thinking", "text": thinking_to_yield}
                    break

    if buffer:
        chunk_type = "thinking" if in_thinking else "content"
        yield {"type": chunk_type, "text": buffer}



__all__ = ["stream_with_thinking_separation"]
