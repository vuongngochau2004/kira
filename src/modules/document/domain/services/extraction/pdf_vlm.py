"""PDF extraction using VLM (Vision Language Model) transcription.

Renders each PDF page to an image and transcribes it using an
Ollama-compatible VLM API. Supports page-level verification and
legal document canonicalization. All VLM-specific helpers are self-contained.
"""

import asyncio
import base64
import html
import json
import logging
import re
from dataclasses import asdict
from io import BytesIO
from pathlib import Path

from src.modules.document.domain.constants import VIETNAMESE_DIACRITICS
from src.modules.document.domain.models import ExtractionResult
from src.modules.document.domain.services.quality_checker import (
    analyze_vietnamese_text_quality,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# VLM Helpers (Self-contained within VLM module)
# ---------------------------------------------------------------------------


def _clean_vlm_markdown(text: str) -> str:
    """Light cleanup that removes model formatting artifacts without rewriting content."""
    cleaned = text.strip()
    cleaned = re.sub(r"^\s*```(?:markdown|md|text)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    cleaned = html.unescape(cleaned).replace("\xa0", " ")
    cleaned = re.sub(r"[ \t]{3,}", "  ", cleaned)
    cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)
    return cleaned.strip()


def _meaningful_char_count(text: str) -> int:
    cleaned = html.unescape(text).replace("\xa0", " ")
    cleaned = re.sub(r"```(?:markdown|md|text)?|```", "", cleaned, flags=re.IGNORECASE)
    return sum(1 for char in cleaned if char.isalnum() or char in VIETNAMESE_DIACRITICS)


def _meaningful_coverage_ratio(source_text: str, final_text: str) -> float:
    """Estimate whether cleanup/verification dropped too much visible content."""
    source_count = _meaningful_char_count(source_text)
    if source_count == 0:
        return 1.0
    final_count = _meaningful_char_count(final_text)
    return round(final_count / source_count, 4)


def _prepare_vlm_image_data_url(image_bytes: bytes) -> str:
    """Resize and compress rendered page image before sending it to the VLM."""
    from PIL import Image

    from src.config.config import settings

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    max_side = settings.vlm_image_max_side
    if max(image.size) > max_side:
        image.thumbnail((max_side, max_side))

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=settings.vlm_image_jpeg_quality, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


async def _transcribe_page_with_ollama_vlm(
    image_data_url: str,
    page_number: int,
) -> str:
    """Transcribe a rendered PDF page through Ollama's OpenAI-compatible VLM API."""
    import httpx

    from src.config.config import settings

    api_key = settings.ollama_api_keys.split(",", 1)[0].strip()
    if not api_key:
        raise RuntimeError("OLLAMA_API_KEYS is required for VLM transcription")

    prompt = (
        "Bạn là hệ thống transcription tài liệu hành chính tiếng Việt.\n"
        "Hãy chép lại nguyên văn nội dung chính nhìn thấy trên trang ảnh.\n"
        "Không tóm tắt, không diễn giải, không thêm nội dung không có trong ảnh.\n"
        "Giữ nguyên số quyết định, ngày tháng, tên cơ quan, Điều/Khoản/Điểm.\n"
        "Bỏ qua dấu mộc, watermark, chữ trang trí hoặc nhiễu ảnh nếu không thuộc nội dung chính.\n"
        "Sửa lỗi chữ rõ ràng khi ảnh cho thấy chắc chắn.\n"
        "Trả về Markdown sạch, chỉ gồm nội dung trang.\n"
        "Không bọc trong ```markdown hoặc code fence.\n"
        "Không dùng HTML entity như &nbsp;; dùng khoảng trắng thường hoặc bảng Markdown đơn giản.\n"
        f"Trang: {page_number}.\n"
    )

    payload = {
        "model": settings.ollama_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url},
                    },
                ],
            }
        ],
        "temperature": 0,
        "max_tokens": settings.vlm_transcription_max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions"

    async with httpx.AsyncClient(timeout=settings.vlm_transcription_timeout) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"].strip()


async def _verify_page_with_ollama_vlm(
    image_data_url: str,
    page_number: int,
    transcription_text: str,
) -> str:
    """Correct and verify a page transcription against the source image."""
    import httpx

    from src.config.config import settings

    api_key = settings.ollama_api_keys.split(",", 1)[0].strip()
    if not api_key:
        raise RuntimeError("OLLAMA_API_KEYS is required for VLM verification")

    prompt = (
        "Bạn là hệ thống kiểm chứng và hiệu chỉnh transcription tài liệu pháp quy tiếng Việt.\n"
        "Dựa vào ảnh gốc là nguồn sự thật chính. Transcription bên dưới chỉ là bản nháp.\n"
        "Nhiệm vụ:\n"
        "- Sửa lỗi transcription rõ ràng theo ảnh gốc.\n"
        "- Giữ nguyên số quyết định, ngày tháng, tên cơ quan, Điều/Khoản/Điểm.\n"
        "- Không tóm tắt, không diễn giải, không thêm nội dung mới.\n"
        "- Bỏ watermark/dấu mộc/chữ nhiễu không thuộc nội dung chính.\n"
        "- Trả Markdown sạch cho riêng trang này.\n"
        "- Không bọc trong ```markdown hoặc code fence.\n"
        "- Không dùng HTML entity như &nbsp;; dùng khoảng trắng thường hoặc bảng Markdown đơn giản.\n"
        f"Trang: {page_number}.\n\n"
        "Transcription bước 1:\n"
        "```markdown\n"
        f"{transcription_text[:6000]}\n"
        "```\n\n"
    )

    payload = {
        "model": settings.ollama_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            }
        ],
        "temperature": 0,
        "max_tokens": settings.vlm_transcription_max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions"

    async with httpx.AsyncClient(timeout=settings.vlm_transcription_timeout) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"].strip()


async def _canonicalize_legal_document_with_ollama(text: str) -> str:
    """Normalize a verified document into legal structure without adding content."""
    import httpx

    from src.config.config import settings

    if len(text) > settings.legal_canonicalization_max_chars:
        raise ValueError(
            "document too large for single-pass canonicalization "
            f"({len(text)} > {settings.legal_canonicalization_max_chars} chars)"
        )

    api_key = settings.ollama_api_keys.split(",", 1)[0].strip()
    if not api_key:
        raise RuntimeError("OLLAMA_API_KEYS is required for legal canonicalization")

    prompt = (
        "Bạn là hệ thống chuẩn hóa văn bản pháp quy tiếng Việt sau OCR/VLM.\n"
        "Đầu vào đã được kiểm chứng theo ảnh từng trang, nhưng có thể còn ngắt dòng/trang chưa tốt.\n"
        "Hãy tạo canonical_text để dùng cho chunking và embedding.\n\n"
        "Yêu cầu bắt buộc:\n"
        "- Không tóm tắt, không diễn giải, không thêm nội dung mới.\n"
        "- Giữ nguyên nghĩa, số quyết định, ngày tháng, tên cơ quan, căn cứ pháp lý.\n"
        "- Giữ lại marker dạng <!-- page n --> gần vị trí nội dung gốc để audit.\n"
        "- Chuẩn hóa heading Chương/Điều/Phụ lục thành Markdown rõ ràng.\n"
        "- Giữ Khoản dạng số 1., 2., 3. và Điểm dạng a), b), c) khi có trong tài liệu.\n"
        "- Nếu nội dung bảng/phụ lục có cấu trúc, giữ bằng Markdown đơn giản dễ đọc.\n"
        "- Chỉ trả về canonical Markdown, không ghi chú thêm.\n\n"
        "Văn bản đã verify:\n"
        "```markdown\n"
        f"{text}\n"
        "```"
    )

    payload = {
        "model": settings.ollama_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max(settings.vlm_transcription_max_tokens, 8192),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions"

    async with httpx.AsyncClient(timeout=settings.vlm_transcription_timeout) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    canonical_text = data["choices"][0]["message"]["content"].strip()
    if not canonical_text:
        raise ValueError("canonicalization returned empty text")
    return canonical_text


def _audit_document_dir(file_path: str) -> Path:
    """Return audit directory for a source file."""
    from src.config.config import settings

    slug = re.sub(r"[^a-zA-Z0-9]+", "_", Path(file_path).stem).strip("_")[:120]
    audit_dir = Path(settings.document_audit_dir) / (slug or "document")
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir


def _write_vlm_audit_artifacts(
    audit_dir: Path,
    pages: list[dict],
    canonical_text: str,
    metadata: dict,
) -> Path:
    """Write page images, VLM page output, canonical text, and quality metadata."""
    pages_dir = audit_dir / "pages"
    raw_dir = audit_dir / "raw"
    canonical_dir = audit_dir / "canonical"
    pages_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    canonical_dir.mkdir(parents=True, exist_ok=True)

    from PIL import Image

    page_summaries = []
    for page in pages:
        page_number = page["page"]
        image = Image.open(BytesIO(page["image_bytes"])).convert("RGB")
        image.save(pages_dir / f"page_{page_number:03d}.jpg", format="JPEG", quality=90)
        (raw_dir / f"page_{page_number:03d}_vlm_transcription.md").write_text(
            page["transcription"],
            encoding="utf-8",
        )
        (canonical_dir / f"page_{page_number:03d}.md").write_text(
            page["canonical_text"],
            encoding="utf-8",
        )
        page_summaries.append(
            {
                "page": page_number,
                "quality": page["quality"],
            }
        )

    (canonical_dir / "canonical_text.md").write_text(canonical_text, encoding="utf-8")
    metadata = {**metadata, "pages": page_summaries}
    (canonical_dir / "quality_report.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return audit_dir


# ---------------------------------------------------------------------------
# Main VLM Extractor
# ---------------------------------------------------------------------------


async def extract_pdf_vlm(file_path: str) -> ExtractionResult:
    """Extract PDF text by rendering each page and transcribing it with a VLM."""
    logger.info("Extracting PDF using VLM transcription: %s", file_path)
    try:
        import fitz

        from src.config.config import settings

        doc = fitz.open(file_path)
        zoom = settings.pdf_render_dpi / 72
        audit_dir = _audit_document_dir(file_path) if settings.document_audit_enabled else None
        rendered_pages: list[dict] = []

        for page_num, page in enumerate(doc):
            logger.info("VLM rendering page %d/%d for %s", page_num + 1, len(doc), file_path)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            image_bytes = pix.tobytes("png")
            rendered_pages.append(
                {
                    "page_index": page_num,
                    "page_number": page_num + 1,
                    "image_bytes": image_bytes,
                    "image_data_url": _prepare_vlm_image_data_url(image_bytes),
                }
            )
        doc.close()

        semaphore = asyncio.Semaphore(max(1, settings.vlm_page_concurrency))

        async def process_page(rendered_page: dict) -> dict:
            page_number = rendered_page["page_number"]
            async with semaphore:
                logger.info("VLM transcribing page %d/%d", page_number, len(rendered_pages))
                text = await _transcribe_page_with_ollama_vlm(
                    image_data_url=rendered_page["image_data_url"],
                    page_number=page_number,
                )

                cleaned_text = _clean_vlm_markdown(text)
                initial_quality = analyze_vietnamese_text_quality(
                    cleaned_text,
                    lang=settings.ocr_lang,
                    fallback_score=settings.docling_quality_fallback_score,
                )
                should_verify = settings.vlm_page_verification_enabled and (
                    not settings.vlm_verify_only_failed_pages or initial_quality.should_fallback
                )
                verified = False
                canonical_text = cleaned_text
                if should_verify:
                    logger.info("VLM verifying page %d/%d", page_number, len(rendered_pages))
                    canonical_text = await _verify_page_with_ollama_vlm(
                        image_data_url=rendered_page["image_data_url"],
                        page_number=page_number,
                        transcription_text=cleaned_text,
                    )
                    canonical_text = _clean_vlm_markdown(canonical_text)
                    verified = True

                final_quality = analyze_vietnamese_text_quality(
                    canonical_text,
                    lang=settings.ocr_lang,
                    fallback_score=settings.docling_quality_fallback_score,
                )
                coverage_ratio = _meaningful_coverage_ratio(cleaned_text, canonical_text)
                warnings = []
                if final_quality.should_fallback:
                    warnings.append("page_quality_failed")
                if coverage_ratio < settings.vlm_min_page_coverage_ratio:
                    warnings.append("page_coverage_too_low")

                return {
                    "page_index": rendered_page["page_index"],
                    "page": page_number,
                    "image_bytes": rendered_page["image_bytes"],
                    "transcription": text,
                    "canonical_text": canonical_text,
                    "verified": verified,
                    "coverage_ratio": coverage_ratio,
                    "quality": asdict(final_quality),
                    "initial_quality": asdict(initial_quality),
                    "warnings": warnings,
                }

        processed_pages = await asyncio.gather(
            *(process_page(rendered_page) for rendered_page in rendered_pages)
        )
        processed_pages.sort(key=lambda page: page["page_index"])
        page_texts = [(page["page_index"], page["canonical_text"]) for page in processed_pages]
        page_reports = [
            {
                "page": page["page"],
                "chars": len(page["canonical_text"]),
                "verified": page["verified"],
                "coverage_ratio": page["coverage_ratio"],
                "warnings": page["warnings"],
                "initial_quality": page["initial_quality"],
                "quality": page["quality"],
            }
            for page in processed_pages
        ]

        full_text = "\n\n".join(
            f"<!-- page {page_num + 1} -->\n{text.strip()}"
            for page_num, text in page_texts
            if text.strip()
        )
        canonicalization = {
            "enabled": settings.legal_canonicalization_enabled,
            "applied": False,
            "error": None,
        }
        if settings.legal_canonicalization_enabled and full_text.strip():
            try:
                logger.info("Canonicalizing verified VLM text for %s", file_path)
                full_text = await _canonicalize_legal_document_with_ollama(full_text)
                full_text = _clean_vlm_markdown(full_text)
                canonicalization["applied"] = True
            except Exception as e:
                canonicalization["error"] = f"{type(e).__name__}: {e}"
                logger.warning("Legal canonicalization failed for %s: %r", file_path, e)

        final_quality = analyze_vietnamese_text_quality(
            full_text,
            lang=settings.ocr_lang,
            fallback_score=settings.docling_quality_fallback_score,
        )
        page_warnings = [
            {
                "page": page["page"],
                "warnings": page["warnings"],
            }
            for page in processed_pages
            if page["warnings"]
        ]
        quality_status = "pass"
        if final_quality.should_fallback or page_warnings:
            quality_status = "needs_review"
        audit_path = None
        if audit_dir:
            audit_path = _write_vlm_audit_artifacts(
                audit_dir=audit_dir,
                pages=processed_pages,
                canonical_text=full_text,
                metadata={
                    "source_file": file_path,
                    "extractor": "vlm-ollama",
                    "model": settings.ollama_model,
                    "render_dpi": settings.pdf_render_dpi,
                    "page_concurrency": settings.vlm_page_concurrency,
                    "verify_only_failed_pages": settings.vlm_verify_only_failed_pages,
                    "canonicalization": canonicalization,
                    "quality_status": quality_status,
                    "page_warnings": page_warnings,
                    "final_quality": asdict(final_quality),
                },
            )

        return ExtractionResult(
            text=full_text,
            pages=len(page_texts),
            page_texts=page_texts,
            metadata={
                "extractor": "vlm-ollama",
                "engine": "ollama",
                "model": settings.ollama_model,
                "ocr_used": False,
                "ocr_engine": None,
                "extraction_method": "vlm",
                "render_dpi": settings.pdf_render_dpi,
                "page_concurrency": settings.vlm_page_concurrency,
                "verify_only_failed_pages": settings.vlm_verify_only_failed_pages,
                "canonicalization": canonicalization,
                "quality_status": quality_status,
                "page_warnings": page_warnings,
                "page_quality": page_reports,
                "final_quality": asdict(final_quality),
                "audit_path": str(audit_path) if audit_path else None,
            },
            success=bool(full_text.strip()),
            error=None if full_text.strip() else "VLM extraction returned empty text",
        )
    except Exception as e:
        logger.error("VLM PDF extraction failed for %s: %r", file_path, e)
        return ExtractionResult(
            success=False,
            error=f"VLM PDF extraction failed: {type(e).__name__}: {e!r}",
        )


__all__ = [
    "extract_pdf_vlm",
    "_prepare_vlm_image_data_url",
    "_transcribe_page_with_ollama_vlm",
    "_clean_vlm_markdown",
]
