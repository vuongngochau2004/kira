"""Backward compatibility shim - Re-exports from new server structure.

This file maintains backward compatibility for existing imports:
    from src.main import app, create_app

The actual implementation has moved to: src.server.main

This shim will be removed in Phase 10 after all references updated.
"""

from src.server.main import app, create_app

__all__ = ["app", "create_app"]
