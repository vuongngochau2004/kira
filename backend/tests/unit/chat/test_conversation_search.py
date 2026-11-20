"""Regression checks for owner-scoped conversation search and pagination."""

from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from kira.chat.repository import list_conversations


class _CountResult:
    def scalar_one(self) -> int:
        return 2


class _RowsResult:
    def scalars(self) -> "_RowsResult":
        return self

    def all(self) -> list[object]:
        return []


class _RecordingSession:
    def __init__(self) -> None:
        self.statements: list[object] = []

    async def execute(self, statement: object) -> _CountResult | _RowsResult:
        self.statements.append(statement)
        return _CountResult() if len(self.statements) == 1 else _RowsResult()


@pytest.mark.asyncio
async def test_search_scopes_count_and_page_to_owner_and_treats_wildcards_literally() -> None:
    user_id = uuid4()
    session = _RecordingSession()

    rows, total = await list_conversations(
        user_id=user_id,
        db=session,  # type: ignore[arg-type] - statement recorder replaces the DB adapter
        search="  100%_policy  ",
        limit=20,
        offset=20,
    )

    assert rows == []
    assert total == 2
    for statement in session.statements:
        compiled = statement.compile(dialect=postgresql.dialect())
        assert "conversations.user_id" in str(compiled)
        assert "conversations.deleted_at IS NULL" in str(compiled)
        assert "conversations.title ILIKE" in str(compiled)
        assert user_id in compiled.params.values()
        assert any("100\\%\\_policy" in str(value) for value in compiled.params.values())

    page = session.statements[1].compile(dialect=postgresql.dialect())
    assert 20 in page.params.values()
