"""Progressive PDF extraction: native-first + hybrid (PaddleOCR → VLM fallback).

Escalation ladder:
    1. Try cheap native extraction (Docling).
    2. If native text is clean and acceptable, accept it directly (fastest).
    3. If native fails or is poor quality, escalate to Hybrid OCR/VLM cascade.
"""

import logging
from dataclasses import asdict

from src.modules.document.domain.models import ExtractionResult
from src.modules.document.domain.services.extraction.pdf_docling import extract_pdf_docling
from src.modules.document.domain.services.extraction.pdf_vlm import (
    _clean_vlm_markdown,
    _prepare_vlm_image_data_url,
    _transcribe_page_with_ollama_vlm,
)
from src.modules.document.domain.services.quality_checker import (
    analyze_vietnamese_text_quality,
)
from src.shared.ports.ocr import OCRPort

logger = logging.getLogger(__name__)


async def extract_pdf_progressive(
    file_path: str,
    use_ocr_fallback: bool = True,
    ocr: OCRPort | None = None,
) -> ExtractionResult:
    """Progressive PDF extraction: native-first + hybrid (PaddleOCR -> VLM fallback)."""
    from src.config.config import settings

    logger.info("Progressive extraction starting for %s", file_path)

    # Step 1: native extraction via Docling (fast, free, no external calls)
    native_result = await extract_pdf_docling(file_path)
    if native_result.success and native_result.text.strip():
        native_text = native_result.text
        total_pages = max(native_result.pages, 1)

        quality = analyze_vietnamese_text_quality(
            native_text,
            lang=settings.ocr_lang,
            fallback_score=settings.docling_quality_fallback_score,
        )
        if not quality.should_fallback:
            logger.info(
                "Progressive: native text is clean and accepted (chars=%d, pages=%d)",
                len(native_text),
                total_pages,
            )
            native_result.metadata.update(
                {
                    "progressive_path": "native_trusted",
                    "progressive_quality": asdict(quality),
                }
            )
            return native_result

    # Step 2: Escalate to Hybrid OCR/VLM cascade
    logger.info("Progressive: Escalating to Hybrid OCR/VLM cascade for %s", file_path)

    if ocr is None:
        from src.shared.adapters.ocr.paddleocr_adapter import PaddleOCRAdapter

        ocr = PaddleOCRAdapter()

    try:
        import fitz

        doc = fitz.open(file_path)
        total_pages = len(doc)
        zoom = settings.pdf_render_dpi / 72

        page_texts = []
        hybrid_metadata = {
            "progressive_path": "hybrid_cascade",
            "paddleocr_pages": [],
            "vlm_pages": [],
        }

        for page_num in range(total_pages):
            page = doc[page_num]
            logger.info("Hybrid processing page %d/%d for %s", page_num + 1, total_pages, file_path)

            # Render page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            image_bytes = pix.tobytes("png")

            # Run local PaddleOCR
            logger.info("Page %d: Running PaddleOCR...", page_num + 1)
            try:
                page_text = await ocr.extract_text(image_bytes, language=settings.ocr_lang)
            except Exception as ocr_err:
                logger.warning(
                    "PaddleOCR failed on page %d: %s. Forcing VLM.", page_num + 1, ocr_err
                )
                page_text = ""

            # Analyze OCR quality for this page
            quality = analyze_vietnamese_text_quality(
                page_text,
                lang=settings.ocr_lang,
                fallback_score=settings.docling_quality_fallback_score,
            )

            # Decide if VLM is needed
            if quality.should_fallback or not page_text.strip():
                logger.info(
                    "Page %d: OCR quality low (score=%d, issues=%s). Escalating to VLM...",
                    page_num + 1,
                    quality.score,
                    quality.issues,
                )
                image_data_url = _prepare_vlm_image_data_url(image_bytes)
                vlm_text = await _transcribe_page_with_ollama_vlm(
                    image_data_url=image_data_url,
                    page_number=page_num + 1,
                )
                vlm_cleaned = _clean_vlm_markdown(vlm_text)

                page_texts.append(vlm_cleaned)
                hybrid_metadata["vlm_pages"].append(page_num + 1)
            else:
                logger.info("Page %d: OCR quality acceptable. Keeping OCR text.", page_num + 1)
                page_texts.append(page_text)
                hybrid_metadata["paddleocr_pages"].append(page_num + 1)

        doc.close()

        full_text = "\n\n".join(
            f"<!-- page {i + 1} -->\n{text.strip()}"
            for i, text in enumerate(page_texts)
            if text.strip()
        )

        return ExtractionResult(
            text=full_text,
            pages=total_pages,
            page_texts=[(i + 1, text) for i, text in enumerate(page_texts)],
            metadata=hybrid_metadata,
            success=bool(full_text.strip()),
        )

    except Exception as e:
        logger.error("Hybrid OCR/VLM extraction failed for %s: %s", file_path, e)
        return ExtractionResult(
            success=False,
            error=f"Hybrid extraction failed: {e}",
        )


__all__ = ["extract_pdf_progressive"]
