"""Grouped document response models for RAG system.

This module defines user-friendly response structures where chunks are
grouped by their source documents, making it clear which documents and how
many chunks were used in generating the answer.

Senior Dev Notes:
- Groups chunks by document for better UX
- Provides aggregate statistics per document
- Maintains backward compatibility with legacy systems
- Frontend-friendly structure (easy to visualize)
"""

from dataclasses import dataclass, field
from typing import Any
from pydantic import BaseModel, Field


@dataclass(frozen=True)
class ChunkInfo:
    """Immutable chunk information with metadata.

    Attributes:
        chunk_id: Unique chunk identifier
        page: Page number (if available)
        snippet: Preview of chunk content (first N chars)
        score: Relevance score from retrieval
    """
    chunk_id: str
    page: int | None = None
    snippet: str = ""
    score: float = 0.0


class SourceChunk(BaseModel):
    """Individual chunk within a document source.

    Represents a single retrieved chunk with its metadata.
    """
    chunk_id: str = Field(..., description="Unique chunk identifier (e.g., 'doc_123_chunk_5')")
    page: int | None = Field(None, description="Page number where chunk is located")
    snippet: str = Field(..., description="Preview of chunk content (first 200 chars)")
    score: float = Field(..., ge=0.0, le=1.0, description="Retrieval relevance score")
    content: str | None = Field(None, description="Full chunk content (optional, for debugging)")


class DocumentSource(BaseModel):
    """Document with its associated chunks.

    Groups all chunks from the same document together with aggregate
    statistics. This structure makes it clear which documents contributed
    to the answer and how many chunks were used from each.

    Attributes:
        document_id: Unique document identifier
        filename: Original filename
        title: Document title
        total_chunks_used: Number of chunks from this document used in context
        relevance_score: Aggregate relevance score for this document
        chunks: List of chunks retrieved from this document
    """
    document_id: str = Field(..., description="Unique document identifier (e.g., 'doc_123')")
    filename: str = Field(..., description="Original filename (e.g., 'quy_che_tot_nghiep.pdf')")
    title: str = Field(..., description="Document title")
    total_chunks_used: int = Field(..., ge=0, description="Number of chunks from this document in context")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Aggregate relevance for this document")
    chunks: list[SourceChunk] = Field(default_factory=list, description="Chunks retrieved from this document")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "document_id": "doc_123",
                    "filename": "quy_che_tot_nghiep.pdf",
                    "title": "Quy chế xét tốt nghiệp",
                    "total_chunks_used": 4,
                    "relevance_score": 0.87,
                    "chunks": [
                        {
                            "chunk_id": "doc_123_chunk_5",
                            "page": 5,
                            "snippet": "Điều kiện xét tốt nghiệp...",
                            "score": 0.92
                        }
                    ]
                }
            ]
        }
    }


class SourceMetadata(BaseModel):
    """Aggregate metadata about sources used.

    Provides high-level statistics about the retrieval process,
    useful for analytics and UI display.
    """
    total_documents: int = Field(..., ge=0, description="Total number of unique documents used")
    total_chunks: int = Field(..., ge=0, description="Total number of chunks used")
    top_document: str = Field(..., description="Filename of most relevant document")


class GroupedDocumentResponse(BaseModel):
    """RAG response with grouped document structure.

    This is the new user-friendly response format where chunks are
    grouped by their source documents, making it easy to see:
    - Which documents contributed to the answer
    - How many chunks from each document
    - Aggregate relevance per document

    Example:
        ```python
        {
            "content": "Để xét tốt nghiệp...",
            "sources": [
                {
                    "document_id": "doc_123",
                    "filename": "quy_che_tot_nghiep.pdf",
                    "title": "Quy chế xét tốt nghiệp",
                    "total_chunks_used": 4,
                    "relevance_score": 0.87,
                    "chunks": [...]
                }
            ],
            "metadata": {
                "total_documents": 2,
                "total_chunks": 5,
                "top_document": "quy_che_tot_nghiep.pdf"
            }
        }
        ```
    """
    content: str = Field(..., description="Generated answer text")
    sources: list[DocumentSource] = Field(
        default_factory=list,
        description="Documents with their chunks, grouped by source"
    )
    metadata: SourceMetadata = Field(..., description="Aggregate statistics about sources")

    # Legacy fields for backward compatibility (deprecated)
    citations: list[dict] = Field(
        default_factory=list,
        deprecated=True,
        description="Legacy field - use 'sources' instead"
    )

    def get_legacy_citations(self) -> list[dict]:
        """Convert grouped structure to legacy citations format.

        Useful for systems that haven't migrated to the new structure yet.

        Returns:
            List of citation dicts in legacy flat format
        """
        legacy_citations = []

        for doc_source in self.sources:
            for chunk in doc_source.chunks:
                legacy_citations.append({
                    "chunk_id": chunk.chunk_id,
                    "source": doc_source.filename,
                    "title": doc_source.title,
                    "snippet": chunk.snippet,
                    "page_number": chunk.page,
                    "score": chunk.score,
                    "document_id": doc_source.document_id,
                })

        return legacy_citations

    def get_flat_chunks(self) -> list[SourceChunk]:
        """Get all chunks in a flat list (across all documents).

        Returns:
            List of all chunks from all documents
        """
        flat_chunks = []
        for doc_source in self.sources:
            flat_chunks.extend(doc_source.chunks)
        return flat_chunks


# Legacy alias for backward compatibility
DocumentGroup = DocumentSource
__all__ = [
    "ChunkInfo",
    "SourceChunk",
    "DocumentSource",
    "SourceMetadata",
    "GroupedDocumentResponse",
]
