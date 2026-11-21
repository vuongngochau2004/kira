"""Application service for enriching chat citations."""

from kira.retrieval.search import PostgresRetrievalDocumentAdapter


class EnrichCitations:
    """Resolve citation document IDs to display names without HTTP concerns."""

    def __init__(self, documents: PostgresRetrievalDocumentAdapter):
        self._documents = documents

    async def execute(self, citations: list[dict]) -> list[dict]:
        document_ids = list(
            {
                str(
                    citation.get("document_id")
                    or (citation.get("metadata") or {}).get("document_id")
                )
                for citation in citations
                if citation.get("document_id")
                or (citation.get("metadata") or {}).get("document_id")
            }
        )
        if not document_ids:
            return citations
        filenames = await self._documents.get_filenames(document_ids)
        for citation in citations:
            document_id = citation.get("document_id") or (citation.get("metadata") or {}).get(
                "document_id"
            )
            filename = filenames.get(str(document_id))
            if filename:
                citation.update({"filename": filename, "source": filename, "title": filename})
        return citations


__all__ = ["EnrichCitations"]
