from datetime import date

from src.shared.adapters.graph import cypher
from src.shared.adapters.graph.neo4j_adapter import context_from_record


class _Neo4jDate:
    def __init__(self, value: date) -> None:
        self._value = value

    def to_native(self) -> date:
        return self._value


def test_context_from_record_converts_neo4j_dates() -> None:
    context = context_from_record(
        {
            "key": "31/2024/QH15#D3.K1",
            "parent_label": "Điều 3",
            "parent_text": "Điều 3. Quyền của Nhà nước",
            "introduced_by": None,
            "introduced_by_number": None,
            "introduced_by_title": None,
            "amended_after": _Neo4jDate(date(2026, 7, 1)),
        }
    )
    assert context.provision_key == "31/2024/QH15#D3.K1"
    assert context.amended_after == date(2026, 7, 1)
    assert context.parent_label == "Điều 3"


def test_read_queries_are_parameterised() -> None:
    assert "$keys" in cypher.EXPAND_CONTEXT and "$day" in cypher.EXPAND_CONTEXT
    assert "GUIDES" in cypher.GUIDING_DOCUMENTS
    assert any("provision_document_number" in s for s in cypher.SCHEMA_STATEMENTS)
