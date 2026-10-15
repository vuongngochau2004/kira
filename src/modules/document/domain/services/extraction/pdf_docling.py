"""PDF extraction using Docling document converter."""

import asyncio
import logging

from src.modules.document.domain.models import ExtractionResult

logger = logging.getLogger(__name__)


async def extract_pdf_docling(file_path: str) -> ExtractionResult:
    """Extract PDF text using Docling."""
    logger.info("Extracting PDF using Docling: %s", file_path)
    try:
        import fitz
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = await asyncio.to_thread(converter.convert, file_path)
        text = result.document.export_to_markdown()

        pages = 0
        try:
            doc = fitz.open(file_path)
            pages = len(doc)
            doc.close()
        except Exception:
            pages = 1

        return ExtractionResult(
            text=text,
            pages=pages,
            page_texts=[(0, text)] if text.strip() else [],
            metadata={
                "extractor": "docling",
                "engine": "docling",
                "ocr_used": True,
                "extraction_method": "docling",
            },
            success=bool(text.strip()),
        )
    except Exception as e:
        logger.error("Docling PDF extraction failed for %s: %s", file_path, e)
        return ExtractionResult(
            success=False,
            error=f"Docling PDF extraction failed: {e}",
        )


__all__ = ["extract_pdf_docling"]
