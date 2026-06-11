"""PaddleOCR Adapter — implements OCRPort.

Wraps the existing PaddleOCRClient from
src.modules.document.infrastructure.ocr.ocr_client.
"""
from src.shared.ports.ocr import OCRPort
from src.modules.document.infrastructure.ocr.ocr_client import get_ocr_client


class PaddleOCRAdapter(OCRPort):
    """Adapter for PaddleOCR HTTP service."""

    async def extract_text(self, image_bytes: bytes, language: str = "vi") -> str:
        """Extract text from image bytes using PaddleOCR service."""
        client = get_ocr_client()
        result = await client.ocr_image_bytes(image_bytes, lang=language)
        if not result.success:
            raise RuntimeError(f"OCR processing failed: {result.error}")
        return result.text

    async def health_check(self) -> bool:
        """Check health of the PaddleOCR service."""
        client = get_ocr_client()
        return await client.check_health()
