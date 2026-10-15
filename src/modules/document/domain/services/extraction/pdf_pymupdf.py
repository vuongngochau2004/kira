"""PDF extraction using PyMuPDF (fitz) with PaddleOCR fallback for scanned pages."""

import logging

from src.modules.document.domain.models import ExtractionResult
from src.modules.document.domain.services.quality_checker import is_low_quality_text
from src.shared.ports.ocr import OCRPort

logger = logging.getLogger(__name__)


async def extract_pdf_pymupdf(
    file_path: str,
    use_ocr_fallback: bool = True,
    force_ocr_all: bool = False,
    ocr: OCRPort | None = None,
) -> ExtractionResult:
    """Extract text from PDF using PyMuPDF with PaddleOCR fallback for scanned pages."""
    logger.info("Extracting PDF using PyMuPDF (native text): %s", file_path)
    try:
        import fitz

        from src.config.config import settings

        doc = fitz.open(file_path)
        num_pages = len(doc)
        text_parts = []
        page_texts = []  # Track (page_num, text) for citation page tracking
        pages_needing_ocr = []
        ocr_lang = settings.ocr_lang

        # First pass: extract text with PyMuPDF
        for page_num, page in enumerate(doc):
            page_text = page.get_text()
            if force_ocr_all:
                text_parts.append(page_text)
                pages_needing_ocr.append(page_num)
                continue

            # If the page has text and it is of acceptable quality, keep it.
            # Otherwise, route the page to OCR.
            if page_text.strip() and not is_low_quality_text(page_text, lang=ocr_lang):
                text_parts.append(page_text)
                page_texts.append((page_num, page_text))  # Track page number
            else:
                # Mark page for OCR - use placeholder
                text_parts.append("")  # Placeholder for OCR result
                pages_needing_ocr.append(page_num)

        # If all pages have text or OCR disabled, return early
        if not pages_needing_ocr or not use_ocr_fallback:
            doc.close()
            full_text = "\n\n".join(
                f"<!-- page {page_num + 1} -->\n{text.strip()}"
                for page_num, text in enumerate(text_parts)
                if text.strip()
            )
            return ExtractionResult(
                text=full_text,
                pages=num_pages,
                page_texts=page_texts,  # Include page tracking
                metadata={
                    "extractor": "pymupdf",
                    "engine": "fitz",
                    "ocr_used": False,
                    "extraction_method": "normal",
                },
                success=bool(full_text.strip()),
            )

        # Second pass: OCR for pages without text
        if ocr is None:
            return ExtractionResult(
                success=False, error="OCR fallback requested without an OCRPort"
            )
        for page_num in pages_needing_ocr:
            page = doc[page_num]

            # Convert page to image
            mat = fitz.Matrix(3.0, 3.0)  # 3x zoom for better OCR
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")

            # Perform OCR
            ocr_text = await ocr.extract_text(img_bytes, language=ocr_lang)

            if ocr_text.strip():
                # Update placeholder with OCR text
                text_parts[page_num] = ocr_text
                page_texts.append((page_num, ocr_text))  # Track OCR pages too
            elif text_parts[page_num].strip():
                page_texts.append((page_num, text_parts[page_num]))

        doc.close()

        full_text = "\n\n".join(
            f"<!-- page {page_num + 1} -->\n{text.strip()}"
            for page_num, text in enumerate(text_parts)
            if text.strip()
        )

        return ExtractionResult(
            text=full_text,
            pages=num_pages,
            page_texts=page_texts,  # Include page tracking
            metadata={
                "extractor": "pymupdf-ocr-hybrid",
                "engine": "fitz",
                "ocr_used": True,
                "ocr_pages": len(pages_needing_ocr),
                "extraction_method": "ocr",
                "force_ocr_all": force_ocr_all,
            },
            success=bool(full_text.strip()),
        )

    except Exception as e:
        logger.error("PyMuPDF extraction failed for %s: %s", file_path, e)
        return ExtractionResult(
            success=False,
            error=f"PDF extraction failed: {e}",
        )


__all__ = ["extract_pdf_pymupdf"]
