"""
Shared Utilities - Common utility functions.

This package contains utility functions used across the application:
- Agent utilities (conversational query detection, JSON parsing)
- Post-processing utilities (thinking separation, formatting)
- Common helper functions

**Main Exports**:
- is_conversational_query: Detect conversational vs research queries
- parse_json_response: Parse JSON from LLM responses
- format_context: Format documents for context
"""

from src.shared.utils.agent import is_conversational_query, parse_json_response, format_context, CONVERSATIONAL_KEYWORDS

__all__ = [
    "is_conversational_query",
    "parse_json_response",
    "format_context",
    "CONVERSATIONAL_KEYWORDS",
]
