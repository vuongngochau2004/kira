"""Extractor for Word documents (.docx)."""

import logging

from src.modules.document.domain.models import ExtractionResult

logger = logging.getLogger(__name__)


def extract_docx(file_path: str) -> ExtractionResult:
    """Extract text from DOCX using python-docx.

    Args:
        file_path: Path to DOCX file

    Returns:
        ExtractionResult with text and metadata
    """
    logger.info("Extracting DOCX using python-docx: %s", file_path)
    try:
        from docx import Document

        doc = Document(file_path)
        text_parts = []

        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)

        full_text = "\n".join(text_parts)

        return ExtractionResult(
            text=full_text,
            pages=1,
            metadata={"extractor": "python-docx", "extraction_method": "normal", "ocr_used": False},
            success=bool(full_text.strip()),
        )
    except Exception as e:
        logger.error("DOCX extraction failed for %s: %s", file_path, e)
        return ExtractionResult(
            success=False,
            error=f"DOCX extraction failed: {e}",
        )


__all__ = ["extract_docx"]
