"""
Protocols package for K.I.R.A architecture refactor.

This package contains Protocol/ABC abstractions for:
- Classification strategies
- Query handlers
- Retrieval operations
- Dependency injection

Following SOLID principles:
- SRP: Each protocol represents single capability
- DIP: High-level modules depend on protocols, not concretions
- OCP: Open for extension (new implementations), closed for modification
"""

from src.protocols.classification import (
    ClassificationStrategy,
    ClassificationResult,
    Intent
)

from src.protocols.handlers import (
    QueryHandler,
    HandlerResult,
    HandlerConfig
)

__all__ = [
    "ClassificationStrategy",
    "ClassificationResult",
    "Intent",
    "QueryHandler",
    "HandlerResult",
    "HandlerConfig",
]
