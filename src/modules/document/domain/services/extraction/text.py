"""Extractor for plain text and markdown files (.txt, .md)."""

import logging

from src.modules.document.domain.models import ExtractionResult

logger = logging.getLogger(__name__)


def extract_text_file(file_path: str) -> ExtractionResult:
    """Extract text from plain text or markdown file.

    Args:
        file_path: Path to text file

    Returns:
        ExtractionResult with text and metadata
    """
    logger.info("Extracting text file: %s", file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        return ExtractionResult(
            text=text,
            pages=1,
            metadata={"extractor": "native", "extraction_method": "normal", "ocr_used": False},
            success=bool(text.strip()),
        )
    except UnicodeDecodeError:
        logger.warning("UTF-8 decoding failed for %s, falling back to latin-1", file_path)
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                text = f.read()
            return ExtractionResult(
                text=text,
                pages=1,
                metadata={
                    "extractor": "native",
                    "encoding": "latin-1",
                    "extraction_method": "normal",
                    "ocr_used": False,
                },
                success=True,
            )
        except Exception as e:
            logger.error("Text file extraction failed for %s with latin-1: %s", file_path, e)
            return ExtractionResult(
                success=False,
                error=f"Text extraction failed: {e}",
            )
    except Exception as e:
        logger.error("Text file extraction failed for %s: %s", file_path, e)
        return ExtractionResult(
            success=False,
            error=f"Text extraction failed: {e}",
        )


__all__ = ["extract_text_file"]
