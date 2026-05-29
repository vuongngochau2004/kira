"""Document extraction using PyMuPDF (Docling fallback)."""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@dataclass
class ExtractionResult:
    """Result from text extraction."""
    text: str = ""
    pages: int = 0
    metadata: dict = field(default_factory=dict)
    success: bool = True
    error: str | None = None


SUPPORTED_TYPES = {
    "pdf", "docx", "pptx", "xlsx", "html", "md", "txt",
}

OCR_TYPES = {"png", "jpg", "jpeg", "tiff", "bmp", "gif", "webp"}


def extract_pdf(file_path: str) -> ExtractionResult:
    """Extract text from PDF using PyMuPDF (fitz).

    Args:
        file_path: Path to PDF file

    Returns:
        ExtractionResult with text and metadata
    """
    try:
        import fitz
        doc = fitz.open(file_path)
        text_parts = []

        for page_num, page in enumerate(doc):
            page_text = page.get_text()
            if page_text.strip():
                text_parts.append(page_text)

        doc.close()

        full_text = "\n\n".join(text_parts)

        return ExtractionResult(
            text=full_text,
            pages=len(text_parts),
            metadata={"extractor": "pymupdf", "engine": "fitz"},
            success=bool(full_text.strip()),
        )
    except Exception as e:
        return ExtractionResult(
            success=False,
            error=f"PyMuPDF extraction failed: {e}",
        )


def extract_docx(file_path: str) -> ExtractionResult:
    """Extract text from DOCX using python-docx.

    Args:
        file_path: Path to DOCX file

    Returns:
        ExtractionResult with text and metadata
    """
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
            metadata={"extractor": "python-docx"},
            success=bool(full_text.strip()),
        )
    except Exception as e:
        return ExtractionResult(
            success=False,
            error=f"DOCX extraction failed: {e}",
        )


def extract_pptx(file_path: str) -> ExtractionResult:
    """Extract text from PPTX using python-pptx.

    Args:
        file_path: Path to PPTX file

    Returns:
        ExtractionResult with text and metadata
    """
    try:
        from pptx import Presentation

        prs = Presentation(file_path)
        text_parts = []

        for slide in prs.slides:
            slide_text = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text)
            if slide_text:
                text_parts.append("\n".join(slide_text))

        full_text = "\n\n".join(text_parts)

        return ExtractionResult(
            text=full_text,
            pages=len(prs.slides),
            metadata={"extractor": "python-pptx"},
            success=bool(full_text.strip()),
        )
    except Exception as e:
        return ExtractionResult(
            success=False,
            error=f"PPTX extraction failed: {e}",
        )


def extract_text_file(file_path: str) -> ExtractionResult:
    """Extract text from plain text or markdown file.

    Args:
        file_path: Path to text file

    Returns:
        ExtractionResult with text and metadata
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        return ExtractionResult(
            text=text,
            pages=1,
            metadata={"extractor": "native"},
            success=bool(text.strip()),
        )
    except UnicodeDecodeError:
        # Try with different encoding
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                text = f.read()
            return ExtractionResult(
                text=text,
                pages=1,
                metadata={"extractor": "native", "encoding": "latin-1"},
                success=True,
            )
        except Exception as e:
            return ExtractionResult(
                success=False,
                error=f"Text extraction failed: {e}",
            )
    except Exception as e:
        return ExtractionResult(
            success=False,
            error=f"Text extraction failed: {e}",
        )


def extract_image_ocr(file_path: str) -> ExtractionResult:
    """Extract text from image using OCR (Docling).

    Args:
        file_path: Path to image file

    Returns:
        ExtractionResult with text and metadata
    """
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(file_path)

        text = result.document.export_to_markdown()

        return ExtractionResult(
            text=text,
            pages=1,
            metadata={"extractor": "docling-ocr"},
            success=bool(text.strip()),
        )
    except Exception as e:
        return ExtractionResult(
            success=False,
            error=f"Image OCR failed: {e}",
        )


def extract_content(file_path: str, file_type: str) -> ExtractionResult:
    """Extract text from file using appropriate extractor.

    Args:
        file_path: Path to the file
        file_type: File extension (e.g., "pdf", "docx")

    Returns:
        ExtractionResult with text, pages, metadata
    """
    from pathlib import Path

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

    try:
        if file_type == "pdf":
            return extract_pdf(file_path)
        elif file_type == "docx":
            return extract_docx(file_path)
        elif file_type == "pptx":
            return extract_pptx(file_path)
        elif file_type in {"txt", "md"}:
            return extract_text_file(file_path)
        elif file_type in OCR_TYPES:
            return extract_image_ocr(file_path)
        else:
            return ExtractionResult(
                success=False,
                error=f"Format {file_type} not yet supported",
            )
    except Exception as e:
        return ExtractionResult(
            success=False,
            error=f"Extraction failed: {e}",
        )


__all__ = [
    "ExtractionResult",
    "extract_content",
    "extract_pdf",
    "extract_docx",
    "extract_pptx",
    "extract_text_file",
    "extract_image_ocr",
]
