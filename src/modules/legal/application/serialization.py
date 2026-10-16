"""JSON serialization of parsed provisions stored in legal_documents.parsed_structure."""

from collections.abc import Mapping, Sequence
from typing import Any

from src.modules.legal.domain.models import ParsedProvision, ProvisionLevel


def provisions_to_json(provisions: Sequence[ParsedProvision]) -> list[dict[str, Any]]:
    return [
        {
            "provision_key": provision.provision_key,
            "level": provision.level.value,
            "label": provision.label,
            "heading": provision.heading,
            "chapter_label": provision.chapter_label,
            "text": provision.text,
            "page": provision.page,
            "parent_key": provision.parent_key,
        }
        for provision in provisions
    ]


def provisions_from_json(rows: Sequence[Mapping[str, Any]]) -> list[ParsedProvision]:
    return [
        ParsedProvision(
            provision_key=row["provision_key"],
            level=ProvisionLevel(row["level"]),
            label=row["label"],
            heading=row.get("heading", ""),
            chapter_label=row.get("chapter_label"),
            text=row["text"],
            page=row.get("page"),
            parent_key=row.get("parent_key"),
        )
        for row in rows
    ]
