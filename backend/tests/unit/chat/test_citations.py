"""Tests for kira.chat.citations."""

import pytest

from kira.chat.citations import EnrichCitations


class FakeDocuments:
    def __init__(self):
        self.calls = []

    async def get_filenames(self, document_ids):
        self.calls.append(document_ids)
        return {document_ids[0]: "quy-che.pdf"}


@pytest.mark.asyncio
async def test_citation_enrichment_preserves_unknown_citations():
    port = FakeDocuments()
    citations = [{"document_id": "doc-1"}, {"filename": "already-known.pdf"}]

    result = await EnrichCitations(port).execute(citations)

    assert port.calls == [["doc-1"]]
    assert result[0]["filename"] == "quy-che.pdf"
    assert result[1]["filename"] == "already-known.pdf"
