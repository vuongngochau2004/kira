"""Semantic router configuration."""

from pydantic import Field


class SemanticRouterConfig:
    """Semantic router settings."""

    # Similarity threshold
    threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for routing decision",
    )

    # Enable/disable semantic routing
    enabled: bool = Field(
        default=True,
        description="Enable semantic routing layer",
    )

    # Fallback to LLM if below threshold
    fallback_to_llm: bool = Field(
        default=True,
        description="Fallback to LLM classifier when score < threshold",
    )


# Default configuration
default_config = SemanticRouterConfig()


__all__ = ["SemanticRouterConfig", "default_config"]
