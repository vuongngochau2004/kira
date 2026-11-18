"""Unit tests for VbplScraper adapter."""

from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.modules.legal.application.errors import InvalidLegalDocumentInput
from src.modules.legal.infrastructure.scrapers.vbpl_scraper import (
    VbplScraper,
    normalize_doc_type,
    parse_date,
)

SAMPLE_TABLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Văn bản 123/2020/NĐ-CP</title></head>
<body>
    <table>
        <tr><td>Số ký hiệu</td><td>123/2020/NĐ-CP</td></tr>
        <tr><td>Loại văn bản</td><td>Nghị định</td></tr>
        <tr><td>Trích yếu</td><td>Quy định về hóa đơn, chứng từ điện tử</td></tr>
        <tr><td>Cơ quan ban hành</td><td>Chính phủ</td></tr>
        <tr><td>Ngày ban hành</td><td>19/10/2020</td></tr>
        <tr><td>Ngày có hiệu lực</td><td>01/07/2022</td></tr>
    </table>
    <div class="content">
        <a href="/Files/vanban123.pdf">Tải văn bản gốc PDF</a>
    </div>
</body>
</html>
"""

SAMPLE_RAW_HTML_NO_ATTACHMENT = """
<!DOCTYPE html>
<html>
<head><title>Hệ thống VBPL - Luật Đất đai</title></head>
<body>
    <h1>Luật Đất đai số 31/2024/QH15</h1>
    <p>Loại văn bản: Luật</p>
    <p>Cơ quan ban hành: Quốc hội</p>
    <p>Ngày ban hành: 18/01/2024</p>
    <p>Ngày có hiệu lực: 01/08/2024</p>
    <div class="toan-van">
        Điều 1. Phạm vi điều chỉnh...
    </div>
</body>
</html>
"""


def test_normalize_doc_type():
    assert normalize_doc_type("Nghị định của Chính phủ") == "decree"
    assert normalize_doc_type("Luật Đất đai") == "law"
    assert normalize_doc_type("Thông tư số 12") == "circular"
    assert normalize_doc_type("Quyết định") == "decision"
    assert normalize_doc_type("Nghị quyết Quốc hội") == "resolution"
    assert normalize_doc_type("Chỉ thị của Thủ tướng") == "other"


def test_parse_date():
    assert parse_date("19/10/2020") == date(2020, 10, 19)
    assert parse_date("ban hành ngày 01-07-2022") == date(2022, 7, 1)
    assert parse_date("invalid date") is None


def test_validate_url():
    scraper = VbplScraper()
    scraper.validate_url("https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=123")
    scraper.validate_url("http://danang.vbpl.vn/pages/vanban.aspx")

    with pytest.raises(InvalidLegalDocumentInput, match="URL must be from vbpl.vn"):
        scraper.validate_url("https://google.com/test")

    with pytest.raises(InvalidLegalDocumentInput, match="Invalid URL protocol"):
        scraper.validate_url("ftp://vbpl.vn/test")


@pytest.mark.asyncio
async def test_scrape_with_attachment():
    scraper = VbplScraper()

    # Mock httpx responses
    mock_page_resp = AsyncMock(spec=httpx.Response)
    mock_page_resp.status_code = 200
    mock_page_resp.text = SAMPLE_TABLE_HTML
    mock_page_resp.raise_for_status = lambda: None

    mock_pdf_resp = AsyncMock(spec=httpx.Response)
    mock_pdf_resp.status_code = 200
    mock_pdf_resp.content = b"%PDF-1.7 mock content" * 10
    mock_pdf_resp.headers = {"content-type": "application/pdf"}

    async def mock_get(url, *args, **kwargs):
        if url.endswith(".pdf"):
            return mock_pdf_resp
        return mock_page_resp

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        result = await scraper.scrape("https://vbpl.vn/TW/Pages/vbpq-thuoctinh.aspx?ItemID=123")

    assert result.metadata.number == "123/2020/NĐ-CP"
    assert result.metadata.doc_type == "decree"
    assert result.metadata.title == "Quy định về hóa đơn, chứng từ điện tử"
    assert result.metadata.issuer == "Chính phủ"
    assert result.metadata.issued_date == date(2020, 10, 19)
    assert result.metadata.effective_date == date(2022, 7, 1)
    assert result.file_name == "vanban123.pdf"
    assert result.content == b"%PDF-1.7 mock content" * 10
    assert result.content_type == "application/pdf"


@pytest.mark.asyncio
async def test_scrape_fallback_html():
    scraper = VbplScraper()

    mock_page_resp = AsyncMock(spec=httpx.Response)
    mock_page_resp.status_code = 200
    mock_page_resp.text = SAMPLE_RAW_HTML_NO_ATTACHMENT
    mock_page_resp.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", return_value=mock_page_resp):
        result = await scraper.scrape("https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=999")

    assert result.metadata.number == "31/2024/QH15"
    assert result.metadata.doc_type == "law"
    assert result.metadata.issuer == "Quốc hội"
    assert result.metadata.issued_date == date(2024, 1, 18)
    assert result.metadata.effective_date == date(2024, 8, 1)
    assert result.file_name.endswith(".html")
    assert result.content_type.startswith("text/html")
    assert b"Lu\xe1\xba\xadt \xc4\x90\xe1\xba\xa5t \xc4\x91ai" in result.content

