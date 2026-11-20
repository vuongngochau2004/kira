"""Scraper adapter for fetching legal documents from vbpl.vn."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from html import unescape
from urllib.parse import unquote, urljoin, urlparse

import httpx
from loguru import logger

from src.modules.legal.application.errors import InvalidLegalDocumentInput
from src.modules.legal.application.records import LegalDocumentMetadata
from src.modules.legal.application.upload_document import LEGAL_DOCUMENT_TYPES
from src.modules.legal.domain.extraction.rules import DOCUMENT_NUMBER_PATTERN

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://vbpl.vn/",
    "Connection": "keep-alive",
}

_DOC_TYPE_MAPPING: dict[str, str] = {
    "luật": "law",
    "bộ luật": "law",
    "nghị định": "decree",
    "thông tư": "circular",
    "thông tư liên tịch": "circular",
    "quyết định": "decision",
    "nghị quyết": "resolution",
    "lệnh": "other",
    "chỉ thị": "other",
}

_DATE_PATTERN = re.compile(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})")
_ATTACHMENT_PATTERN = re.compile(r'href=["\']([^"\']+\.(?:pdf|docx|doc|txt))["\']', re.IGNORECASE)


@dataclass(frozen=True)
class ScrapedLegalDocument:
    """Standardized scraped legal document payload ready for UploadLegalDocument."""

    metadata: LegalDocumentMetadata
    file_name: str
    content: bytes
    content_type: str


def normalize_doc_type(raw_type: str) -> str:
    """Normalize Vietnamese document type to application doc_type enum."""
    raw_lower = raw_type.strip().lower()
    for prefix, mapped in _DOC_TYPE_MAPPING.items():
        if raw_lower.startswith(prefix) or prefix in raw_lower:
            return mapped
    return "other" if "other" in LEGAL_DOCUMENT_TYPES else "law"


def parse_date(date_str: str) -> date | None:
    """Parse date from common Vietnamese string formats (DD/MM/YYYY)."""
    match = _DATE_PATTERN.search(date_str)
    if not match:
        return None
    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    try:
        return date(year, month, day)
    except ValueError:
        return None


def clean_html_text(html: str) -> str:
    """Remove scripts, styles and strip HTML tags while preserving text structure."""
    text = re.sub(r"<script\b.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"</div>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


class VbplScraper:
    """Scraper adapter for fetching and parsing legal documents from vbpl.vn."""

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def validate_url(self, url: str) -> None:
        """Verify URL belongs to vbpl.vn domain."""
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"}:
            raise InvalidLegalDocumentInput(f"Invalid URL protocol: {url}")
        host = parsed.netloc.lower()
        if host != "vbpl.vn" and not host.endswith(".vbpl.vn"):
            raise InvalidLegalDocumentInput(f"URL must be from vbpl.vn domain, got: {host}")

    async def scrape(self, url: str) -> ScrapedLegalDocument:
        """Fetch page, extract metadata and download attachment or fallback to HTML."""
        self.validate_url(url)
        clean_url = url.strip()

        async with httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
            timeout=self._timeout,
        ) as client:
            try:
                response = await client.get(clean_url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error("Failed to fetch vbpl page {}: {}", clean_url, exc)
                raise InvalidLegalDocumentInput(f"Could not connect to vbpl.vn: {exc}") from exc

            html = response.text
            metadata = self._extract_metadata(html=html, source_url=clean_url)

            # Try downloading attached file
            file_payload = await self._fetch_attachment(
                client=client, base_url=clean_url, html=html
            )
            if file_payload is not None:
                file_name, content, content_type = file_payload
            else:
                # Fallback: clean HTML to standalone HTML document
                sanitized_num = re.sub(r"[^\w\-.]", "_", metadata.number)
                file_name = f"{sanitized_num}.html"
                content = html.encode("utf-8")
                content_type = "text/html; charset=utf-8"

            return ScrapedLegalDocument(
                metadata=metadata,
                file_name=file_name,
                content=content,
                content_type=content_type,
            )

    def _extract_metadata(self, html: str, source_url: str) -> LegalDocumentMetadata:
        """Extract metadata fields from HTML using table labels and heuristics."""
        # 1. Number
        number = self._extract_field(
            html,
            patterns=[
                r"(?:Số\s*(?:hiệu|ký\s*hiệu)?|Số\s*:)\s*</td>\s*<td[^>]*>(.*?)</td>",
                r"(?:Số\s*(?:hiệu|ký\s*hiệu)?|Số\s*:)\s*[\"'>\s]*([0-9]+/[0-9]+/[A-ZĐ0-9\-]+)",
            ],
        )
        if not number:
            match = DOCUMENT_NUMBER_PATTERN.search(html)
            if match:
                number = match.group(1)

        if not number or DOCUMENT_NUMBER_PATTERN.fullmatch(number.strip()) is None:
            # Try finding any document number pattern in the text
            clean_text = clean_html_text(html)
            match = DOCUMENT_NUMBER_PATTERN.search(clean_text)
            if match:
                number = match.group(1)
            else:
                raise InvalidLegalDocumentInput(
                    "Could not detect valid legal document number from vbpl.vn page"
                )

        number = number.strip()

        # 2. Document type
        raw_doc_type = self._extract_field(
            html,
            patterns=[
                r"Loại\s*văn\s*bản\s*:?\s*</td>\s*<td[^>]*>(.*?)</td>",
                r"Loại\s*văn\s*bản\s*:?\s*<[^>]+>\s*([^<]+)",
                r"Loại\s*văn\s*bản\s*:\s*([^<\n]+)",
            ],
        )
        doc_type = normalize_doc_type(raw_doc_type or "")

        # 3. Title / Trích yếu
        title = self._extract_field(
            html,
            patterns=[
                r"Trích\s*yếu\s*:?\s*</td>\s*<td[^>]*>(.*?)</td>",
                r"Trích\s*yếu\s*:?\s*<[^>]+>\s*([^<]+)",
                r"Trích\s*yếu\s*:\s*([^<\n]+)",
                r"<title>\s*(.*?)\s*</title>",
            ],
        )
        if not title:
            title = f"Văn bản pháp luật {number}"
        else:
            title = re.sub(r"\s+", " ", title).strip()
            # Clean common title prefixes if title was taken from <title>
            title = re.sub(r"^Hệ thống VBPL\s*-\s*", "", title, flags=re.I)
            title = re.sub(r"\s*-\s*Cơ sở dữ liệu quốc gia về pháp luật$", "", title, flags=re.I)

        # 4. Issuer / Cơ quan ban hành
        issuer = self._extract_field(
            html,
            patterns=[
                r"Cơ\s*quan\s*ban\s*hành\s*:?\s*</td>\s*<td[^>]*>(.*?)</td>",
                r"Cơ\s*quan\s*ban\s*hành\s*:?\s*<[^>]+>\s*([^<]+)",
                r"Cơ\s*quan\s*ban\s*hành\s*:\s*([^<\n]+)",
            ],
        )
        if not issuer:
            issuer = "Chính phủ"

        issuer = re.sub(r"\s+", " ", issuer).strip()

        # 5. Issued date / Ngày ban hành
        raw_issued = self._extract_field(
            html,
            patterns=[
                r"Ngày\s*ban\s*hành\s*:?\s*</td>\s*<td[^>]*>(.*?)</td>",
                r"Ngày\s*ban\s*hành\s*:?\s*<[^>]+>\s*([^<]+)",
                r"Ngày\s*ban\s*hành\s*:\s*([^<\n]+)",
            ],
        )
        issued_date = parse_date(raw_issued or "") if raw_issued else None

        # 6. Effective date / Ngày có hiệu lực
        raw_effective = self._extract_field(
            html,
            patterns=[
                r"Ngày\s*có\s*hiệu\s*lực\s*:?\s*</td>\s*<td[^>]*>(.*?)</td>",
                r"Ngày\s*có\s*hiệu\s*lực\s*:?\s*<[^>]+>\s*([^<]+)",
                r"Ngày\s*có\s*hiệu\s*lực\s*:\s*([^<\n]+)",
            ],
        )
        effective_date = parse_date(raw_effective or "") if raw_effective else None

        # Fallback if dates missing
        today = datetime.now().date()
        if not issued_date:
            issued_date = today
        if not effective_date:
            effective_date = issued_date

        if effective_date < issued_date:
            effective_date = issued_date

        return LegalDocumentMetadata(
            number=number,
            doc_type=doc_type,
            title=title,
            issuer=issuer,
            issued_date=issued_date,
            effective_date=effective_date,
            source_url=source_url,
        )

    def _extract_field(self, html: str, patterns: list[str]) -> str | None:
        """Search regex patterns and return first cleaned captured group."""
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
            if match:
                raw_val = match.group(1)
                cleaned = clean_html_text(raw_val)
                if cleaned:
                    return cleaned
        return None

    async def _fetch_attachment(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        html: str,
    ) -> tuple[str, bytes, str] | None:
        """Find attachment download link in HTML and download binary content."""
        matches = _ATTACHMENT_PATTERN.findall(html)
        if not matches:
            return None

        # Prioritize pdf, docx, doc
        priorities = [".pdf", ".docx", ".doc", ".txt"]
        sorted_links = sorted(
            matches,
            key=lambda link: next(
                (i for i, ext in enumerate(priorities) if link.lower().endswith(ext)),
                len(priorities),
            ),
        )

        for relative_link in sorted_links:
            target_url = urljoin(base_url, relative_link)
            try:
                res = await client.get(target_url)
                if res.status_code == 200 and len(res.content) > 100:
                    raw_filename = unquote(target_url.rsplit("/", 1)[-1])
                    content_type = res.headers.get("content-type", "application/octet-stream")
                    return raw_filename, res.content, content_type
            except Exception as exc:
                logger.warning("Failed to download attachment {}: {}", target_url, exc)
                continue

        return None
