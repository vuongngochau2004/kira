"""Shared infrastructure modules.

Cross-cutting infrastructure concerns shared across all modules:
- auth: JWT authentication, CSRF protection, route dependencies
- monitoring: Routing metrics, agentic metrics, dashboard config
- persistence: Database session, ORM models, query helpers
"""

__all__ = [
    "auth",
    "monitoring",
    "persistence",
]