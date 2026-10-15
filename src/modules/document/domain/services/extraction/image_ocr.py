"""Extractor for scanned images (PNG, JPG, TIFF, etc.) using OCR."""

import logging
from pathlib import Path

from src.modules.document.domain.models import ExtractionResult
from src.shared.ports.ocr import OCRPort

logger = logging.getLogger(__name__)


async def extract_image_docling(file_path: str, error: str | None = None) -> ExtractionResult:
    """Fallback image extraction using Docling OCR.

    Args:
        file_path: Path to image file
        error: Original error that triggered fallback

    Returns:
        ExtractionResult with text and metadata
    """
    logger.info("Extracting image using Docling OCR: %s", file_path)
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(file_path)
        text = result.document.export_to_markdown()

        return ExtractionResult(
            text=text,
            pages=1,
            metadata={"extractor": "docling-ocr", "fallback_from": "paddleocr"},
            success=bool(text.strip()),
        )
    except Exception as e:
        fallback_err = str(e)
        return ExtractionResult(
            success=False,
            error=f"Image OCR failed (PaddleOCR: {error}, Docling: {fallback_err})",
        )


async def extract_image_ocr(file_path: str, ocr: OCRPort | None = None) -> ExtractionResult:
    """Extract text from image using PaddleOCR service with Docling fallback.

    Args:
        file_path: Path to image file
        ocr: OCRPort adapter instance

    Returns:
        ExtractionResult with text and metadata
    """
    try:
        if ocr is None:
            raise RuntimeError("Image extraction requires an OCRPort")
        result = await ocr.extract_text(Path(file_path).read_bytes())
        if result.strip():
            return ExtractionResult(
                text=result,
                pages=1,
                metadata={
                    "extractor": "paddleocr",
                    "confidence": None,
                },
                success=True,
            )
        else:
            return await extract_image_docling(file_path)

    except Exception as e:
        return await extract_image_docling(file_path, error=str(e))


__all__ = [
    "extract_image_ocr",
    "extract_image_docling",
]
