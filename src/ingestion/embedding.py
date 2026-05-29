"""Embedding service implementation using local sentence-transformers model."""

import asyncio
import sys
from pathlib import Path

import torch
from sentence_transformers import SentenceTransformer

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.config import settings

# Thread-safe lock for lazy initialization
_lock = asyncio.Lock()
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Get or lazy-load the local SentenceTransformer embedding model."""
    global _model
    if _model is None:
        model_name = settings.embedding_model or "AITeamVN/Vietnamese_Embedding_v2"
        print(f"Initializing local SentenceTransformer model: {model_name}...")
        
        # Detect device automatically (GPU if CUDA is available, otherwise CPU)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device for local embedding: {device}")
        
        _model = SentenceTransformer(model_name, device=device)
        
        # Configure sequence length for long-context support
        _model.max_seq_length = 2048
        print(f"Model initialized with max_seq_length = {_model.max_seq_length}")
        
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using the local model.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors (list of floats)
    """
    if not texts:
        return []

    model = _get_model()
    
    # Generate embeddings and normalize to unit vectors
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    
    return embeddings.tolist()


def embed_single(text: str) -> list[float]:
    """Generate embedding for a single text string.

    Args:
        text: Single text string to embed

    Returns:
        Embedding vector as list of floats
    """
    result = embed([text])
    return result[0] if result else []


async def aembed(texts: list[str]) -> list[list[float]]:
    """Async embedding generation using a thread pool.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    # Run the CPU/GPU-bound embedding generation in a separate thread
    # to avoid blocking the FastAPI event loop
    return await asyncio.to_thread(embed, texts)


async def aembed_single(text: str) -> list[float]:
    """Async embedding for a single text string.

    Args:
        text: Single text string to embed

    Returns:
        Embedding vector as list of floats
    """
    result = await aembed([text])
    return result[0] if result else []


def preload_model() -> None:
    """Warm up the embedding model at server startup (forces downloading/loading model)."""
    try:
        print("Preloading local embedding model at startup...")
        _get_model()
        print("Local embedding model is preloaded and ready!")
    except Exception as e:
        print(f"WARNING: Failed to preload local embedding model: {e}")


__all__ = [
    "embed",
    "embed_single",
    "aembed",
    "aembed_single",
    "preload_model",
]
