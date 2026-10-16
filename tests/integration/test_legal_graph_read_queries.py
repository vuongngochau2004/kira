"""Opt-in read-query contract test against the docker-compose Neo4j."""

import os
from datetime import date
from uuid import uuid4

import pytest

from src.shared.adapters.graph.neo4j_adapter import Neo4jLegalGraphAdapter
from src.shared.ports.legal_graph import (
    GraphRelation,
    GraphVersion,
    LegalDocumentNode,
    ProvisionNode,
)

pytestmark = pytest.mark.integration


def _document(number: str, title: str) -> LegalDocumentNode:
    return LegalDocumentNode(
        doc_id=str(uuid4()),
        number=number,
        doc_type="law",
        title=title,
        issuer="Test",
        issued_date=date(2024, 1, 1),
        effective_date=date(2024, 8, 1),
        source_url=None,
        file_key="legal/test.txt",
        sha256="0" * 64,
    )


async def test_expand_context_and_guides() -> None:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("Set RUN_INTEGRATION=1 with Docker services running")

    suffix = uuid4().hex[:8].upper()
    law, amending, decree = f"1/2099/QH{suffix}", f"2/2099/QH{suffix}", f"3/2099/NĐ{suffix}"
    adapter = Neo4jLegalGraphAdapter.from_settings()
    try:
        await adapter.ensure_schema()
        await adapter.upsert_document(_document(law, "Luật Thử"))
        await adapter.upsert_document(_document(amending, "Luật Sửa đổi"))
        await adapter.upsert_document(_document(decree, "Nghị định Thử"))
        await adapter.upsert_provisions(
            [
                ProvisionNode(f"{law}#D1", law, "article", "Điều 1", "Tên", None, None),
                ProvisionNode(f"{law}#D1.K1", law, "clause", "Khoản 1", "", None, f"{law}#D1"),
                ProvisionNode(f"{amending}#D1", amending, "article", "Điều 1", "", None, None),
                ProvisionNode(f"{decree}#D1", decree, "article", "Điều 1", "", None, None),
            ]
        )
        await adapter.replace_provision_timeline(
            f"{law}#D1", [GraphVersion("p1", "Điều 1. Tên", "h", date(2024, 8, 1), None, 1, None)]
        )
        await adapter.replace_provision_timeline(
            f"{law}#D1.K1",
            [
                GraphVersion("k-old", "cũ", "h1", date(2024, 8, 1), date(2026, 7, 1), 1, None),
                GraphVersion("k-new", "mới", "h2", date(2026, 7, 1), None, 1, f"{amending}#D1"),
            ],
        )
        guides = GraphRelation(
            "GUIDES",
            decree,
            f"{decree}#D1",
            law,
            None,
            date(2026, 7, 1),
            "x",
            None,
            str(uuid4()),
            None,
            None,
        )
        await adapter.replace_document_relations(decree, [guides])

        before = await adapter.expand_context([f"{law}#D1.K1"], date(2025, 1, 1))
        context = before[f"{law}#D1.K1"]
        assert (context.parent_label, context.parent_text) == ("Điều 1", "Điều 1. Tên")
        assert context.amended_after == date(2026, 7, 1)
        assert context.introduced_by is None

        after = await adapter.expand_context([f"{law}#D1.K1"], date(2026, 8, 1))
        context = after[f"{law}#D1.K1"]
        assert context.amended_after is None
        assert (
            context.introduced_by,
            context.introduced_by_number,
            context.introduced_by_title,
        ) == (
            f"{amending}#D1",
            amending,
            "Luật Sửa đổi",
        )

        assert await adapter.guiding_documents([f"{law}#D1.K1"]) == [decree]
        assert await adapter.expand_context([], date(2026, 1, 1)) == {}
    finally:
        await adapter._driver.execute_query(
            "MATCH (n) WHERE n.number IN $numbers OR n.document_number IN $numbers "
            "OR any(prefix IN $prefixes WHERE n.provision_key STARTS WITH prefix) "
            "DETACH DELETE n",
            {
                "numbers": [law, amending, decree],
                "prefixes": [f"{law}#", f"{amending}#", f"{decree}#"],
            },
        )
        await adapter.close()
