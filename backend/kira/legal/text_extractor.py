"""Text extraction for legal files, reusing the document module's extractors."""

import tempfile
from pathlib import Path

from kira.documents.processing.cleaner import clean_document
from kira.documents.processing.extractor import extract_content
from kira.legal.errors import LegalTextExtractionError
from kira.legal.ports import LegalTextExtractorPort


class DocumentModuleTextExtractor(LegalTextExtractorPort):
    async def extract_text(self, content: bytes, file_type: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / f"source.{file_type}"
            path.write_bytes(content)
            result = await extract_content(str(path), file_type)
        if not result.success or not result.text.strip():
            raise LegalTextExtractionError(result.error or "No text extracted")
        return clean_document(result.text)
