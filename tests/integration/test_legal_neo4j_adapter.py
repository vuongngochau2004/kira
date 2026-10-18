"""Opt-in contract test against the Neo4j service from docker-compose."""

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


def _document(number: str) -> LegalDocumentNode:
    return LegalDocumentNode(
        doc_id=str(uuid4()),
        number=number,
        doc_type="law",
        title="Test",
        issuer="Test",
        issued_date=date(2024, 1, 1),
        effective_date=date(2024, 8, 1),
        source_url=None,
        file_key="legal/test.txt",
        sha256="0" * 64,
    )


async def test_neo4j_adapter_round_trip() -> None:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("Set RUN_INTEGRATION=1 with Docker services running")

    suffix = uuid4().hex[:8].upper()
    base, amending = f"1/2099/QH{suffix}", f"2/2099/QH{suffix}"
    adapter = Neo4jLegalGraphAdapter.from_settings()
    try:
        assert await adapter.health_check()
        await adapter.ensure_schema()
        await adapter.upsert_document(_document(base))
        await adapter.upsert_document(_document(amending))
        await adapter.upsert_provisions(
            [
                ProvisionNode(f"{base}#D1", base, "article", "Điều 1", "Tên", None, None),
                ProvisionNode(f"{base}#D1.K1", base, "clause", "Khoản 1", "", None, f"{base}#D1"),
                ProvisionNode(f"{amending}#D1", amending, "article", "Điều 1", "Sửa", None, None),
            ]
        )
        old = GraphVersion("v-old", "cũ", "h1", date(2024, 8, 1), date(2026, 7, 1), 1, None)
        new = GraphVersion("v-new", "mới", "h2", date(2026, 7, 1), None, 1, f"{amending}#D1")
        await adapter.replace_provision_timeline(f"{base}#D1.K1", [old])
        await adapter.replace_provision_timeline(f"{base}#D1.K1", [old, new])
        await adapter.replace_provision_timeline(f"{base}#D1.K1", [old, new])
        relation = GraphRelation(
            type="AMENDS",
            source_document=amending,
            source_key=f"{amending}#D1",
            target_number=base,
            target_key=f"{base}#D1.K1",
            effective_date=date(2026, 7, 1),
            evidence_text="Sửa đổi khoản 1 Điều 1",
            evidence_page=1,
            review_id=str(uuid4()),
            approved_by=None,
            approved_at=None,
        )
        await adapter.replace_document_relations(amending, [relation])
        await adapter.replace_document_relations(amending, [relation])

        driver = adapter._driver
        records, _, _ = await driver.execute_query(
            "MATCH (:LegalDocument {number: $base})-[:HAS_PART]->(:Provision)-[:HAS_PART]->"
            "(p:Provision)-[:HAS_VERSION]->(v:ProvisionVersion) "
            "OPTIONAL MATCH (v)-[:INTRODUCED_BY]->(s:Provision) "
            "RETURN p.provision_key AS key, v.version_id AS id, v.valid_to AS valid_to, "
            "s.provision_key AS introduced_by ORDER BY v.valid_from",
            {"base": base},
        )
        assert [(r["id"], r["introduced_by"]) for r in records] == [
            ("v-old", None),
            ("v-new", f"{amending}#D1"),
        ]
        assert records[1]["valid_to"] is None
        rels, _, _ = await driver.execute_query(
            "MATCH ()-[r:AMENDS {source_document: $source}]->() RETURN count(r) AS n",
            {"source": amending},
        )
        assert rels[0]["n"] == 1

        await adapter.replace_provision_timeline(f"{base}#D1.K1", [new])
        remaining, _, _ = await driver.execute_query(
            "MATCH (:Provision {provision_key: $key})-[:HAS_VERSION]->(v) RETURN v.version_id AS id",
            {"key": f"{base}#D1.K1"},
        )
        assert [r["id"] for r in remaining] == ["v-new"]

        await adapter.delete_provisions([f"{base}#D1.K1"])
        gone, _, _ = await driver.execute_query(
            "OPTIONAL MATCH (p:Provision {provision_key: $key}) "
            "OPTIONAL MATCH (v:ProvisionVersion {version_id: 'v-new'}) "
            "RETURN count(p) AS provisions, count(v) AS versions",
            {"key": f"{base}#D1.K1"},
        )
        assert (gone[0]["provisions"], gone[0]["versions"]) == (0, 0)
    finally:
        await adapter._driver.execute_query(
            "MATCH (n) WHERE n.number IN $numbers OR n.document_number IN $numbers "
            "OR n.provision_key STARTS WITH $base OR n.provision_key STARTS WITH $amending "
            "DETACH DELETE n",
            {"numbers": [base, amending], "base": f"{base}#", "amending": f"{amending}#"},
        )
        await adapter.close()
