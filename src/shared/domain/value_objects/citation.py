"""Citation value object.

Re-exports Citation from the shared kernel interfaces where it is
primarily defined, providing a convenient domain-level import path.

Primary definition: src.shared.kernel.interfaces.handlers.Citation
Domain import path: src.shared.domain.value_objects.citation.Citation

Citations represent source references in RAG responses, including
the document filename, page number, relevant text, and confidence score.
"""

# Re-export from kernel interfaces (single source of truth)
from src.shared.kernel.interfaces.handlers import Citation

__all__ = ["Citation"]