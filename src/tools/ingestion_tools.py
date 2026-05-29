"""Ingestion tools for LangChain agent integration."""

import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

from langchain_core.tools import tool

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Global references (to be set by application initialization)
_vector_store_wrapper: Any = None
_document_store: Any = None
_file_store: Any = None


def init_ingestion_tools(
    vector_store_wrapper: Any = None,
    document_store: Any = None,
    file_store: Any = None,
    build_bm25: bool = True,
) -> None:
    """Initialize global ingestion dependencies.

    Args:
        vector_store_wrapper: Vector store instance for embeddings
        document_store: Document store instance for metadata
        file_store: File store instance for raw files
        build_bm25: Whether to initialize BM25 index
    """
    global _vector_store_wrapper, _document_store, _file_store
    _vector_store_wrapper = vector_store_wrapper
    _document_store = document_store
    _file_store = file_store


def _get_vector_store() -> Any:
    """Get the global vector store instance.

    Raises:
        RuntimeError: If vector store has not been initialized
    """
    if _vector_store_wrapper is None:
        raise RuntimeError("Vector store not initialized. Call init_ingestion_tools() first.")
    return _vector_store_wrapper


def _get_document_store() -> Any:
    """Get the global document store instance.

    Raises:
        RuntimeError: If document store has not been initialized
    """
    if _document_store is None:
        raise RuntimeError("Document store not initialized. Call init_ingestion_tools() first.")
    return _document_store


@tool
def extract_text_tool(
    file_path: str,
    file_type: str = "pdf",
) -> str:
    """Extract text content from a document file.

    Supports PDF, DOCX, PPTX, TXT formats.

    Args:
        file_path: Path to the file
        file_type: File type (pdf, docx, pptx, txt)

    Returns:
        JSON string with success status and extracted text
    """
    from src.ingestion.extractor import extract_content_sync

    try:
        result = extract_content_sync(file_path, file_type)

        if result.success:
            return json.dumps({
                "success": True,
                "text": result.text,
                "metadata": result.metadata,
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "success": False,
                "error": result.error or "Extraction failed",
            }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        }, ensure_ascii=False)


@tool
def clean_text_tool(
    text: str,
) -> str:
    """Clean and normalize text content.

    Removes extra whitespace, normalizes unicode,
    and applies text preprocessing rules.

    Args:
        text: Raw text content to clean

    Returns:
        JSON string with cleaned text
    """
    from src.ingestion.cleaner import clean_document

    try:
        cleaned = clean_document(text)

        return json.dumps({
            "success": True,
            "text": cleaned,
            "original_length": len(text),
            "cleaned_length": len(cleaned),
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        }, ensure_ascii=False)


@tool
def chunk_text_tool(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    document_id: str = "unknown",
) -> str:
    """Split text into chunks for embedding and retrieval.

    Args:
        text: Text content to chunk
        chunk_size: Maximum tokens per chunk
        chunk_overlap: Token overlap between chunks
        document_id: Document ID for metadata

    Returns:
        JSON string with list of chunks
    """
    from src.ingestion.chunker import chunk_document

    try:
        chunks = chunk_document(
            text=text,
            document_id=document_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        chunk_data = [
            {
                "index": chunk.index,
                "content": chunk.content,
                "token_count": chunk.token_count,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ]

        return json.dumps({
            "success": True,
            "chunks": chunk_data,
            "total_chunks": len(chunks),
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        }, ensure_ascii=False)


@tool
def embed_chunks_tool(
    chunks: list[dict],
) -> str:
    """Generate embeddings for text chunks.

    Args:
        chunks: List of chunk dicts with 'content' field

    Returns:
        JSON string with embeddings
    """
    from src.ingestion.embedding import embed

    try:
        chunk_texts = [chunk.get("content", "") for chunk in chunks]
        embeddings = embed(chunk_texts)

        return json.dumps({
            "success": True,
            "embeddings": embeddings,
            "count": len(embeddings),
            "dimension": len(embeddings[0]) if embeddings else 0,
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        }, ensure_ascii=False)


__all__ = [
    "init_ingestion_tools",
    "extract_text_tool",
    "clean_text_tool",
    "chunk_text_tool",
    "embed_chunks_tool",
]
