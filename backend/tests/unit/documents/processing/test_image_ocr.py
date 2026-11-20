"""Tests for image extraction through the OCR provider."""

import pytest

from kira.documents.processing.extractor import extract_content


class FakeOCR:
    async def extract_text(self, image_bytes: bytes, language: str = "vi") -> str:
        assert image_bytes == b"fake-image"
        assert language == "vi"
        return "Văn bản đã OCR"

    async def health_check(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_image_extraction_uses_injected_ocr_port(tmp_path):
    image = tmp_path / "scan.png"
    image.write_bytes(b"fake-image")

    result = await extract_content(str(image), "png", ocr=FakeOCR())

    assert result.success is True
    assert result.text == "Văn bản đã OCR"
    assert result.metadata["extractor"] == "paddleocr"
