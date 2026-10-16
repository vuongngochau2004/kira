"""Legal document structure parsing."""

from src.modules.legal.domain.parser.structure import (
    DUPLICATE_PROVISION_KEY_WARNING,
    UNBALANCED_QUOTES_WARNING,
    parse_legal_structure,
)

__all__ = [
    "DUPLICATE_PROVISION_KEY_WARNING",
    "UNBALANCED_QUOTES_WARNING",
    "parse_legal_structure",
]
