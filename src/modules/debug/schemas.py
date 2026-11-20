"""Validated requests for pipeline stage demos."""

from pydantic import BaseModel, Field, field_validator


class ClassifyRequest(BaseModel):
    """One query to classify with the production classifier."""

    query: str = Field(min_length=1, max_length=2000)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """Reject whitespace-only input."""
        if not value.strip():
            raise ValueError("Query must not be blank")
        return value.strip()


class RerankRequest(BaseModel):
    """A query and hand-entered candidates for reranking."""

    query: str = Field(min_length=1, max_length=2000)
    documents: list[str] = Field(min_length=2, max_length=20)
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """Reject whitespace-only input."""
        if not value.strip():
            raise ValueError("Query must not be blank")
        return value.strip()

    @field_validator("documents")
    @classmethod
    def validate_documents(cls, values: list[str]) -> list[str]:
        """Limit candidate size and reject empty entries."""
        if any(not value.strip() or len(value) > 4000 for value in values):
            raise ValueError("Each document must contain 1 to 4000 characters")
        return [value.strip() for value in values]
