"""Document extraction strategies package.

This package contains ONLY format-specific and strategy-specific extractors:
- pdf_progressive.py: Multi-stage progressive PDF extraction (native -> OCR -> VLM)
- pdf_vlm.py: PDF extraction using VLM (Vision Language Model) transcription
- pdf_docling.py: PDF extraction using Docling layout analyzer
- pdf_pymupdf.py: PDF extraction using PyMuPDF native text + PaddleOCR
- docx.py: Word document (.docx) extractor
- pptx.py: PowerPoint (.pptx) extractor
- text.py: Plain text and markdown (.txt, .md) extractor
- image_ocr.py: Scanned image OCR extractor (PaddleOCR + Docling fallback)
"""

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

__all__ = [
    # PDF strategies
    "extract_pdf_progressive",
    "extract_pdf_vlm",
    "extract_pdf_docling",
    "extract_pdf_pymupdf",
    # Office formats
    "extract_docx",
    "extract_pptx",
    # Plain text
    "extract_text_file",
    # Images OCR
    "extract_image_ocr",
    "extract_image_docling",
]
