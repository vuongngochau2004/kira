"""Text extraction for legal files, reusing the document module's extractors."""

import tempfile
from pathlib import Path

from src.modules.document.domain.services.cleaner import clean_document
from src.modules.document.domain.services.extractor import extract_content
from src.modules.legal.application.errors import LegalTextExtractionError
from src.modules.legal.application.ports import LegalTextExtractorPort


class DocumentModuleTextExtractor(LegalTextExtractorPort):
    async def extract_text(self, content: bytes, file_type: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / f"source.{file_type}"
            path.write_bytes(content)
            result = await extract_content(str(path), file_type)
        if not result.success or not result.text.strip():
            raise LegalTextExtractionError(result.error or "No text extracted")
        return clean_document(result.text)
