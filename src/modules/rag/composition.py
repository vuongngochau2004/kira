"""Dependency composition for the RAG module."""

from src.modules.rag.infrastructure.factory import create_default_rag_pipeline_service

__all__ = ["create_default_rag_pipeline_service"]
