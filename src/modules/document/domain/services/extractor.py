"""Document extraction coordinator and facade.

Dispatches extraction requests to concrete extractors in extraction/:
- PDF: pdf_progressive, pdf_vlm, pdf_docling, pdf_pymupdf
- Office: docx, pptx
- Text: text
- Images: image_ocr
"""

import asyncio
import logging
from dataclasses import asdict
from pathlib import Path

from src.modules.document.domain.constants import OCR_TYPES, SUPPORTED_TYPES
from src.modules.document.domain.models import ExtractionResult, TextQualityReport
from src.modules.document.domain.services.extraction.docx import extract_docx
from src.modules.document.domain.services.extraction.image_ocr import (
    extract_image_docling,
    extract_image_ocr,
)
from src.modules.document.domain.services.extraction.pdf_docling import extract_pdf_docling
from src.modules.document.domain.services.extraction.pdf_progressive import (
    extract_pdf_progressive,
)
from src.modules.document.domain.services.extraction.pdf_pymupdf import extract_pdf_pymupdf
from src.modules.document.domain.services.extraction.pdf_vlm import extract_pdf_vlm
from src.modules.document.domain.services.extraction.pptx import extract_pptx
from src.modules.document.domain.services.extraction.text import extract_text_file
from src.modules.document.domain.services.quality_checker import (
    _analyze_vietnamese_text_quality,
    _is_low_quality_text,
    _should_fallback_to_ocr,
    _vietnamese_text_quality_issues,
    analyze_vietnamese_text_quality,
    is_low_quality_text,
    should_fallback_to_ocr,
    vietnamese_text_quality_issues,
)
from src.shared.ports.ocr import OCRPort

logger = logging.getLogger(__name__)


async def extract_pdf(
    file_path: str, use_ocr_fallback: bool = True, ocr: OCRPort | None = None
) -> ExtractionResult:
    """Extract text from PDF using the configured extraction strategy."""
    from src.config.config import settings

    strategy = settings.pdf_extractor.lower()

    if strategy == "progressive":
        return await extract_pdf_progressive(file_path, use_ocr_fallback=use_ocr_fallback, ocr=ocr)

    if strategy == "vlm":
        vlm_result = await extract_pdf_vlm(file_path)
        if vlm_result.success:
            return vlm_result

        logger.warning(
            "VLM PDF extraction failed for %s; falling back to PyMuPDF/OCR: %s",
            file_path,
            vlm_result.error,
        )
        fallback = await extract_pdf_pymupdf(
            file_path,
            use_ocr_fallback=use_ocr_fallback,
            force_ocr_all=True,
            ocr=ocr,
        )
        fallback.metadata["fallback_from"] = "vlm"
        fallback.metadata["vlm_error"] = vlm_result.error
        return fallback

    if strategy == "docling":
        docling_result = await extract_pdf_docling(file_path)
        if docling_result.success:
            quality_report = analyze_vietnamese_text_quality(
                docling_result.text,
                lang=settings.ocr_lang,
                fallback_score=settings.docling_quality_fallback_score,
            )
            if (
                not settings.docling_quality_gate_enabled
                or not quality_report.should_fallback
                or not use_ocr_fallback
            ):
                if quality_report.issues:
                    docling_result.metadata["docling_quality"] = asdict(quality_report)
                return docling_result

            logger.warning(
                "Docling PDF extraction for %s failed quality gate "
                "(score=%d, issues=%s); falling back to PyMuPDF/OCR",
                file_path,
                quality_report.score,
                ", ".join(quality_report.issues),
            )
            fallback = await extract_pdf_pymupdf(
                file_path,
                use_ocr_fallback=use_ocr_fallback,
                force_ocr_all=True,
                ocr=ocr,
            )
            fallback.metadata["fallback_from"] = "docling"
            fallback.metadata["docling_error"] = (
                "Docling output failed Vietnamese quality gate: " + ", ".join(quality_report.issues)
            )
            fallback.metadata["docling_quality"] = asdict(quality_report)
            fallback.metadata["docling_chars"] = len(docling_result.text)
            return fallback

        logger.warning(
            "Docling PDF extraction failed for %s; falling back to PyMuPDF/OCR: %s",
            file_path,
            docling_result.error,
        )

        fallback = await extract_pdf_pymupdf(
            file_path,
            use_ocr_fallback=use_ocr_fallback,
            force_ocr_all=True,
            ocr=ocr,
        )
        fallback.metadata["fallback_from"] = "docling"
        fallback.metadata["docling_error"] = docling_result.error
        return fallback

    return await extract_pdf_pymupdf(file_path, use_ocr_fallback=use_ocr_fallback, ocr=ocr)


async def extract_content(
    file_path: str, file_type: str, ocr: OCRPort | None = None
) -> ExtractionResult:
    """Extract text from file using appropriate extractor."""
    if not Path(file_path).exists():
        return ExtractionResult(
            success=False,
            error=f"File not found: {file_path}",
        )

    file_type = file_type.lower().strip().lstrip(".")

    if file_type not in SUPPORTED_TYPES and file_type not in OCR_TYPES:
        return ExtractionResult(
            success=False,
            error=f"Unsupported file type: {file_type}",
        )

    if file_type == "pdf":
        from src.config.config import settings

        method_name = f"PDF ({settings.pdf_extractor} extractor)"
    elif file_type in OCR_TYPES:
        method_name = "OCR image"
    else:
        method_name = "normal (text-based)"

    print(f"[Extractor] Starting {method_name} extraction for file: {file_path} (format: {file_type})")
    logger.info("Starting %s extraction for file: %s (format: %s)", method_name, file_path, file_type)

    try:
        if file_type == "pdf":
            result = await extract_pdf(file_path, ocr=ocr)
        elif file_type == "docx":
            result = extract_docx(file_path)
        elif file_type == "pptx":
            result = extract_pptx(file_path)
        elif file_type in {"txt", "md"}:
            result = extract_text_file(file_path)
        elif file_type in OCR_TYPES:
            result = await extract_image_ocr(file_path, ocr=ocr)
        else:
            result = ExtractionResult(
                success=False,
                error=f"Format {file_type} not yet supported",
            )

        if result.success:
            if "extraction_method" not in result.metadata:
                is_ocr_result = result.metadata.get("ocr_used", False)
                result.metadata["extraction_method"] = "ocr" if is_ocr_result else "normal"
            if "ocr_used" not in result.metadata:
                result.metadata["ocr_used"] = result.metadata.get("ocr_used", False)

            ext_method = result.metadata["extraction_method"].upper()
            print(f"[Extractor] Extraction successful. Method: {ext_method}, Pages: {result.pages}")
            logger.info(
                "Extraction successful. Method: %s, Pages: %d",
                result.metadata["extraction_method"],
                result.pages,
            )
        else:
            print(f"[Extractor ERROR] Extraction failed: {result.error}")
            logger.error("Extraction failed: %s", result.error)

        return result

    except Exception as e:
        logger.error("Extraction failed for %s: %s", file_path, e)
        return ExtractionResult(
            success=False,
            error=f"Extraction failed: {e}",
        )


def extract_content_sync(
    file_path: str, file_type: str, ocr: OCRPort | None = None
) -> ExtractionResult:
    """Synchronous wrapper for extract_content."""
    return asyncio.run(extract_content(file_path, file_type, ocr=ocr))


# Backward compatibility aliases
_extract_pdf_progressive = extract_pdf_progressive
_extract_pdf_vlm = extract_pdf_vlm
_extract_pdf_docling = extract_pdf_docling
_extract_pdf_pymupdf = extract_pdf_pymupdf
_extract_image_docling = extract_image_docling

__all__ = [
    "ExtractionResult",
    "TextQualityReport",
    "extract_content",
    "extract_content_sync",
    "extract_pdf",
    "extract_docx",
    "extract_pptx",
    "extract_text_file",
    "extract_image_ocr",
    "_extract_image_docling",
    # Quality aliases
    "is_low_quality_text",
    "analyze_vietnamese_text_quality",
    "vietnamese_text_quality_issues",
    "should_fallback_to_ocr",
    "_is_low_quality_text",
    "_analyze_vietnamese_text_quality",
    "_vietnamese_text_quality_issues",
    "_should_fallback_to_ocr",
    # PDF strategy aliases
    "_extract_pdf_progressive",
    "_extract_pdf_vlm",
    "_extract_pdf_docling",
    "_extract_pdf_pymupdf",
]
