from datetime import date, datetime

import pytest

from kira.legal.graph import cypher
from kira.legal.graph.base import GraphRelation, GraphVersion
from kira.legal.graph.neo4j import relation_rows, version_rows
from kira.legal.models import RelationType


def test_relation_types_match_domain() -> None:
    assert set(cypher.RELATION_TYPES) == {member.value for member in RelationType}


def test_relation_query_uses_whitelisted_type() -> None:
    query = cypher.relation_query("AMENDS")
    assert "MERGE (source)-[r:AMENDS {review_id: row.review_id}]->(target)" in query
    with pytest.raises(ValueError):
        cypher.relation_query("AMENDS]->() DETACH DELETE (n")


def test_version_rows_keep_dates_and_nulls() -> None:
    rows = version_rows([GraphVersion("v1", "text", "hash", date(2024, 8, 1), None, 3, None)])
    assert rows == [
        {
            "version_id": "v1",
            "text": "text",
            "text_hash": "hash",
            "valid_from": date(2024, 8, 1),
            "valid_to": None,
            "page": 3,
            "introduced_by": None,
        }
    ]


def test_relation_rows_group_by_type() -> None:
    def relation(rel_type: str, review_id: str) -> GraphRelation:
        return GraphRelation(
            type=rel_type,
            source_document="99/2026/QH15",
            source_key=None,
            target_number="31/2024/QH15",
            target_key=None,
            effective_date=date(2026, 7, 1),
            evidence_text="x",
            evidence_page=None,
            review_id=review_id,
            approved_by=None,
            approved_at=datetime(2026, 6, 1, 8, 0),
        )

    grouped = relation_rows(
        [relation("AMENDS", "a"), relation("BASED_ON", "b"), relation("AMENDS", "c")]
    )
    assert sorted(grouped) == ["AMENDS", "BASED_ON"]
    assert [row["review_id"] for row in grouped["AMENDS"]] == ["a", "c"]
