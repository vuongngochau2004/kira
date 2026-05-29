"""PaddleOCR HTTP API client for OCR processing."""

import asyncio
import base64
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import httpx

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.config import settings


logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result from OCR processing."""
    text: str = ""
    success: bool = True
    error: str | None = None
    confidence: float = 0.0
    raw_response: dict | None = None


class PaddleOCRClient:
    """Client for PaddleOCR HTTP API service."""

    def __init__(
        self,
        base_url: str | None = None,
        lang: str = "vi",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize PaddleOCR client.

        Args:
            base_url: PaddleOCR service base URL
            lang: Language code (vi, en, ch)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts with exponential backoff
        """
        self.base_url = (base_url or settings.ocr_base_url).rstrip("/")
        self.lang = lang
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "PaddleOCRClient":
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def check_health(self) -> bool:
        """Check if OCR service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            await self._ensure_client()
            url = f"{self.base_url}/health"
            response = await self._client.get(url)
            return response.status_code == 200
        except Exception:
            return False

    def _encode_image_bytes(self, image_bytes: bytes) -> str:
        """Encode image bytes to base64 string.

        Args:
            image_bytes: Raw image bytes

        Returns:
            Base64 encoded string
        """
        return base64.b64encode(image_bytes).decode("utf-8")

    async def _request_with_retry(
        self,
        endpoint: str,
        files: dict | None = None,
        data: dict | None = None,
        json: dict | None = None,
    ) -> dict:
        """Make HTTP request with exponential backoff retry.

        Args:
            endpoint: API endpoint path
            files: Files to upload (multipart)
            data: Form data fields (multipart)
            json: JSON payload (legacy / optional)

        Returns:
            Response JSON as dict

        Raises:
            httpx.HTTPError: If all retries exhausted
        """
        await self._ensure_client()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        last_error = None

        for attempt in range(self.max_retries):
            try:
                kwargs = {}
                if files is not None:
                    kwargs["files"] = files
                if data is not None:
                    kwargs["data"] = data
                if json is not None:
                    kwargs["json"] = json

                response = await self._client.post(url, **kwargs)
                response.raise_for_status()
                return response.json() or {}

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"OCR timeout (attempt {attempt + 1}/{self.max_retries}): {e}")

            except httpx.HTTPStatusError as e:
                # Don't retry 4xx errors except 429
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    raise

                last_error = e
                logger.warning(
                    f"OCR HTTP error {e.response.status_code} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )

            except httpx.HTTPError as e:
                last_error = e
                logger.warning(f"OCR request failed (attempt {attempt + 1}/{self.max_retries}): {e}")

            # Exponential backoff before retry
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)

        # All retries exhausted
        raise httpx.HTTPError(
            f"OCR request failed after {self.max_retries} attempts: {last_error}"
        ) from last_error

    async def ocr_image_bytes(
        self,
        image_bytes: bytes,
        lang: str | None = None,
    ) -> OCRResult:
        """Perform OCR on image bytes.

        Args:
            image_bytes: Raw image bytes (PNG, JPG, etc.)
            lang: Language override (uses instance lang if None)

        Returns:
            OCRResult with extracted text and metadata
        """
        if not settings.ocr_enabled:
            return OCRResult(
                success=False,
                error="OCR is disabled in configuration",
            )

        try:
            # Prepare request payload as multipart form-data
            files = {
                "file": ("image.png", image_bytes, "image/png")
            }
            data = {
                "lang": lang or self.lang,
            }

            # Make request with retry
            response_data = await self._request_with_retry("/ocr", files=files, data=data)

            # Extract text from response
            # Common response formats: {"text": "..."} or {"results": [{"text": "..."}]}
            if isinstance(response_data, dict):
                text = response_data.get("text", "")

                # Handle nested results format
                if not text and "results" in response_data:
                    results = response_data.get("results", [])
                    if results and isinstance(results, list):
                        text = " ".join(
                            r.get("text", "") for r in results if isinstance(r, dict)
                        )

                # Get confidence if available
                confidence = response_data.get("confidence", 0.0)
                if not confidence and "lines" in response_data:
                    scores = [line.get("score", 0.0) for line in response_data["lines"] if isinstance(line, dict)]
                    if scores:
                        confidence = sum(scores) / len(scores)

                return OCRResult(
                    text=text,
                    success=bool(text.strip()),
                    confidence=confidence,
                    raw_response=response_data,
                )

            return OCRResult(
                success=False,
                error=f"Unexpected response format: {type(response_data)}",
                raw_response=response_data if isinstance(response_data, dict) else None,
            )

        except httpx.HTTPError as e:
            logger.error(f"OCR HTTP error: {e}")
            return OCRResult(
                success=False,
                error=f"OCR service error: {e}",
            )

        except Exception as e:
            logger.exception(f"OCR processing error: {e}")
            return OCRResult(
                success=False,
                error=f"OCR processing failed: {e}",
            )

    async def ocr_file(self, file_path: str) -> OCRResult:
        """Perform OCR on image file.

        Args:
            file_path: Path to image file

        Returns:
            OCRResult with extracted text
        """
        try:
            with open(file_path, "rb") as f:
                image_bytes = f.read()
            return await self.ocr_image_bytes(image_bytes)
        except FileNotFoundError:
            return OCRResult(
                success=False,
                error=f"File not found: {file_path}",
            )
        except IOError as e:
            return OCRResult(
                success=False,
                error=f"Failed to read file: {e}",
            )


# Singleton client instance
_client: PaddleOCRClient | None = None


def get_ocr_client() -> PaddleOCRClient:
    """Get or create singleton OCR client.

    Returns:
        PaddleOCRClient instance
    """
    global _client
    if _client is None:
        _client = PaddleOCRClient(
            base_url=settings.ocr_base_url,
            lang=settings.ocr_lang,
            timeout=settings.ocr_timeout,
            max_retries=settings.ocr_max_retries,
        )
    return _client


async def close_ocr_client() -> None:
    """Close singleton OCR client."""
    global _client
    if _client:
        await _client.close()
        _client = None


__all__ = [
    "PaddleOCRClient",
    "OCRResult",
    "get_ocr_client",
    "close_ocr_client",
]
