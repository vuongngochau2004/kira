"""Port: OCR provider contract.

Application core depends on this ABC, NOT on PaddleOCR/Tesseract directly.
Allows swapping PaddleOCR ↔ Tesseract ↔ cloud OCR APIs
without changing business logic.
"""
from abc import ABC, abstractmethod


class OCRPort(ABC):
    """Port: what the application needs from any OCR provider.

    Example:
        >>> class MyOCR(OCRPort):
        ...     async def extract_text(self, image_bytes: bytes, language: str = "vi") -> str:
        ...         return "extracted text"
        ...     async def health_check(self) -> bool:
        ...         return True
    """

    @abstractmethod
    async def extract_text(
        self,
        image_bytes: bytes,
        language: str = "vi",
    ) -> str:
        """Extract text from image bytes using OCR.

        Args:
            image_bytes: Raw image content (PNG, JPEG, etc.)
            language: Language code for OCR hint (default: Vietnamese)

        Returns:
            Extracted text as a string
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if OCR service is reachable and operational.

        Returns:
            True if healthy, False otherwise
        """
        ...
