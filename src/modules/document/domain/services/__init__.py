"""Domain services for Document module.

Contains core business logic for document processing.
"""

from src.modules.document.domain.models import Chunk, ExtractionResult
from src.modules.document.domain.services.chunker import (
    chunk_document,
    count_tokens,
)
from src.modules.document.domain.services.cleaner import (
    clean_chunks,
    clean_document,
)
from src.modules.document.domain.services.embedder import (
    aembed,
    aembed_single,
    embed,
    embed_single,
)
from src.modules.document.domain.services.extractor import (
    extract_content,
    extract_content_sync,
    extract_docx,
    extract_image_ocr,
    extract_pdf,
    extract_pptx,
    extract_text_file,
)
from src.modules.document.domain.services.pipeline import (
    process_document,
)
from src.modules.document.domain.services.quality_checker import (
    analyze_vietnamese_text_quality,
    is_low_quality_text,
    should_fallback_to_ocr,
    vietnamese_text_quality_issues,
)
from src.modules.document.domain.services.token_counter import (
    CharacterEncodingFallback,
    TextEncoding,
    get_encoding,
)

__all__ = [
    # Extractor
    "ExtractionResult",
    "extract_content",
    "extract_content_sync",
    "extract_pdf",
    "extract_docx",
    "extract_pptx",
    "extract_text_file",
    "extract_image_ocr",
    # Chunker
    "Chunk",
    "chunk_document",
    "count_tokens",
    # Cleaner
    "clean_document",
    "clean_chunks",
    # Embedder
    "embed",
    "embed_single",
    "aembed",
    "aembed_single",
    # Quality checker
    "is_low_quality_text",
    "analyze_vietnamese_text_quality",
    "vietnamese_text_quality_issues",
    "should_fallback_to_ocr",
    # Token counter
    "TextEncoding",
    "CharacterEncodingFallback",
    "get_encoding",
    # Pipeline
    "process_document",
]
