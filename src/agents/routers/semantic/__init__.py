"""Semantic routing package for KIRA."""

from .config import SemanticRouterConfig, default_config
from .routes import get_all_routes, get_conversational_route, get_rag_legal_route
from .router import KIRASemanticRouter


__all__ = [
    "KIRASemanticRouter",
    "get_conversational_route",
    "get_rag_legal_route",
    "get_all_routes",
    "SemanticRouterConfig",
    "default_config",
]
