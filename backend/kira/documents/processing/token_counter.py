"""Token encoding and counting utilities for text chunking and LLM budget calculation."""

import tiktoken


class CharacterEncodingFallback:
    """Offline fallback when tiktoken cannot load its BPE cache."""

    def encode(self, text: str) -> list[int]:
        return [ord(char) for char in text]

    def decode(self, tokens: list[int]) -> str:
        return "".join(chr(token) for token in tokens)


def get_encoding(encoding_name: str = "cl100k_base") -> tiktoken.Encoding:
    """Retrieve text encoding by name with character fallback."""
    try:
        return tiktoken.get_encoding(encoding_name)
    except Exception:
        return CharacterEncodingFallback()


def count_tokens(
    text: str, encoding: tiktoken.Encoding | None = None, encoding_name: str = "cl100k_base"
) -> int:
    """Count tokens in text using tiktoken or fallback encoding."""
    if encoding is None:
        encoding = get_encoding(encoding_name)
    return len(encoding.encode(text))


# Backward-compatible private aliases
_get_encoding = get_encoding
_count_tokens = count_tokens

__all__ = [
    "CharacterEncodingFallback",
    "get_encoding",
    "count_tokens",
    "_get_encoding",
    "_count_tokens",
]
