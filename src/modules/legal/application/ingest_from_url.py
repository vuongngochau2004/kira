"""Use case for ingesting a legal document by scraping its URL."""

from uuid import UUID

from src.modules.legal.application.records import LegalDocumentRecord
from src.modules.legal.application.upload_document import (
    UploadLegalDocument,
    UploadLegalDocumentRequest,
)
from src.modules.legal.infrastructure.scrapers.vbpl_scraper import VbplScraper


class IngestLegalFromUrl:
    """Orchestrates scraping document metadata & content from a URL and creating an uploaded record."""

    def __init__(self, scraper: VbplScraper, upload_service: UploadLegalDocument) -> None:
        self._scraper = scraper
        self._upload_service = upload_service

    async def execute(self, url: str, uploaded_by: UUID) -> LegalDocumentRecord:
        scraped = await self._scraper.scrape(url)
        upload_request = UploadLegalDocumentRequest(
            metadata=scraped.metadata,
            file_name=scraped.file_name,
            content=scraped.content,
            content_type=scraped.content_type,
            uploaded_by=uploaded_by,
        )
        return await self._upload_service.execute(upload_request)

