"""OCR infrastructure for Document module.

Provides OCR services via PaddleOCR client.
"""

from src.modules.document.infrastructure.ocr.ocr_client import (
    PaddleOCRClient,
    OCRResult,
    get_ocr_client,
    close_ocr_client,
)

__all__ = [
    "PaddleOCRClient",
    "OCRResult",
    "get_ocr_client",
    "close_ocr_client",
]
