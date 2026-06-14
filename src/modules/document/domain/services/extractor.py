"""Document extraction using VLM PDF transcription with legacy OCR fallback.

Migrated from src/ingestion/extractor.py
"""

import asyncio
import base64
import html
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result from text extraction."""
    text: str = ""
    pages: int = 0
    metadata: dict = field(default_factory=dict)
    success: bool = True
    error: str | None = None
    page_texts: list[tuple[int, str]] = field(default_factory=list)  # (page_num, text) for page tracking


@dataclass
class TextQualityReport:
    """Diagnostics for extracted text quality."""

    issues: list[str]
    score: int
    should_fallback: bool
    char_count: int
    word_count: int
    letter_count: int
    vi_diacritic_ratio: float
    unaccented_signal_ratio: float
    mojibake_count: int
    html_entity_count: int
    alphanumeric_artifact_ratio: float


SUPPORTED_TYPES = {
    "pdf", "docx", "pptx", "xlsx", "html", "md", "txt",
}

OCR_TYPES = {"png", "jpg", "jpeg", "tiff", "bmp", "gif", "webp"}

VIETNAMESE_DIACRITICS = set(
    "áàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩị"
    "óòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ"
)

VIETNAMESE_UNACCENTED_SIGNAL_WORDS = {
    "bach", "ban", "bo", "can", "cac", "chinh", "cho", "cong", "cua", "dao",
    "dai", "dan", "danh", "dieu", "dinh", "doc", "duc", "duoc", "giao", "hoc",
    "hoa", "hoat", "hoi", "khoa", "khoan", "ly", "nam", "ngay", "nghi", "nguoi",
    "phuc", "quyet", "quy", "quan", "so", "tac", "tao", "thang", "thinh",
    "to", "truong", "tu", "van", "ve", "viet", "xa",
}

MOJIBAKE_OR_PLACEHOLDER_PATTERN = re.compile(r"[�□ñ]|[A-Za-z][!&*][A-Za-z]")
HTML_ENTITY_PATTERN = re.compile(r"&(?:amp|quot|lt|gt|nbsp);")

QUALITY_ISSUE_WEIGHTS = {
    "low_quality_text": 3,
    "low_vietnamese_diacritics_ratio": 2,
    "many_unaccented_vietnamese_terms": 2,
    "mojibake_or_placeholder_chars": 2,
    "html_entities_in_text": 1,
    "many_alphanumeric_artifacts": 1,
}


def _is_low_quality_text(text: str, lang: str = "vi") -> bool:
    """Detect if the extracted text layer is low-quality, corrupt, or garbage.

    Args:
        text: Extracted text content
        lang: Language for specific diacritics check (default: vi)

    Returns:
        True if the text is low-quality or corrupt, False otherwise
    """
    if not text or not text.strip():
        return True

    cleaned_text = text.strip()
    # If the text is extremely short, treat as no text
    if len(cleaned_text) < 10:
        return True

    # 1. Ratio of single-character words (indicates a broken layout/characters split by spaces)
    words = cleaned_text.split()
    if len(words) > 5:
        single_char_words = [w for w in words if len(w) == 1 and w.isalpha()]
        if len(single_char_words) / len(words) > 0.40:
            logger.warning("Low quality text detected: excessive single-character words (spacing issue)")
            return True

    # 2. Vietnamese-specific diacritics check
    if lang == "vi":
        vi_char_count = sum(1 for c in cleaned_text if c in VIETNAMESE_DIACRITICS)
        total_letters = sum(1 for c in cleaned_text if c.isalpha())

        if total_letters > 20:
            vi_ratio = vi_char_count / total_letters
            # A normal Vietnamese text usually has at least 5% to 15% accented characters.
            # If it's less than 1.5%, it's highly likely a broken or English-only fallback text layer
            if vi_ratio < 0.015:
                logger.warning(
                    "Low quality text detected: very low Vietnamese diacritics ratio (%.2f%%)",
                    vi_ratio * 100
                )
                return True

    return False


def _analyze_vietnamese_text_quality(
    text: str,
    lang: str = "vi",
    fallback_score: int = 3,
) -> TextQualityReport:
    """Analyze whether extracted Vietnamese text should be replaced by OCR.

    The checks are intentionally statistical instead of tied to one PDF template:
    a Vietnamese administrative document with a broken text layer often has many
    common words stripped of diacritics, placeholder/mojibake characters, or HTML
    entities leaked into the exported text. If several of those signals show up
    together, rendered-page OCR is usually more reliable than the embedded text.
    """
    if lang != "vi":
        return TextQualityReport(
            issues=[],
            score=0,
            should_fallback=False,
            char_count=len(text),
            word_count=0,
            letter_count=0,
            vi_diacritic_ratio=0.0,
            unaccented_signal_ratio=0.0,
            mojibake_count=0,
            html_entity_count=0,
            alphanumeric_artifact_ratio=0.0,
        )

    issues: list[str] = []
    if _is_low_quality_text(text, lang=lang):
        issues.append("low_quality_text")

    words = re.findall(r"[A-Za-zÀ-ỹĐđ]+", text.lower())
    ascii_words = [word for word in words if word.isascii()]
    signal_words = [word for word in ascii_words if word in VIETNAMESE_UNACCENTED_SIGNAL_WORDS]

    letter_count = sum(1 for char in text if char.isalpha())
    vi_ratio = 0.0
    if letter_count:
        vi_ratio = sum(1 for char in text if char in VIETNAMESE_DIACRITICS) / letter_count

    if letter_count > 400 and vi_ratio < 0.06:
        issues.append("low_vietnamese_diacritics_ratio")

    signal_ratio = 0.0
    if words:
        signal_ratio = len(signal_words) / len(words)
        if len(words) > 80 and signal_ratio > 0.18 and vi_ratio < 0.14:
            issues.append("many_unaccented_vietnamese_terms")

    mojibake_count = len(MOJIBAKE_OR_PLACEHOLDER_PATTERN.findall(text))
    if mojibake_count >= 3:
        issues.append("mojibake_or_placeholder_chars")

    html_entity_count = len(HTML_ENTITY_PATTERN.findall(text))
    if html_entity_count >= 2:
        issues.append("html_entities_in_text")

    odd_ascii_digit_tokens = re.findall(r"\b[A-Za-z]*\d+[A-Za-z]*\b", text)
    alphanumeric_artifact_ratio = 0.0
    if words:
        alphanumeric_artifact_ratio = len(odd_ascii_digit_tokens) / len(words)
    if len(words) > 80 and alphanumeric_artifact_ratio > 0.03:
        issues.append("many_alphanumeric_artifacts")

    issues = sorted(set(issues))
    score = sum(QUALITY_ISSUE_WEIGHTS.get(issue, 1) for issue in issues)
    should_fallback = score >= fallback_score or "low_quality_text" in issues

    return TextQualityReport(
        issues=issues,
        score=score,
        should_fallback=should_fallback,
        char_count=len(text),
        word_count=len(words),
        letter_count=letter_count,
        vi_diacritic_ratio=round(vi_ratio, 4),
        unaccented_signal_ratio=round(signal_ratio, 4),
        mojibake_count=mojibake_count,
        html_entity_count=html_entity_count,
        alphanumeric_artifact_ratio=round(alphanumeric_artifact_ratio, 4),
    )


def _vietnamese_text_quality_issues(text: str, lang: str = "vi") -> list[str]:
    """Return quality issue names for backward-compatible tests and callers."""
    return _analyze_vietnamese_text_quality(text, lang=lang).issues


def _should_fallback_to_ocr(quality_issues: list[str], fallback_score: int = 3) -> bool:
    """Decide whether quality signals are strong enough to force rendered OCR."""
    if not quality_issues:
        return False

    issue_set = set(quality_issues)
    if "low_quality_text" in issue_set:
        return True

    score = sum(QUALITY_ISSUE_WEIGHTS.get(issue, 1) for issue in issue_set)
    return score >= fallback_score


async def extract_pdf(file_path: str, use_ocr_fallback: bool = True) -> ExtractionResult:
    """Extract text from PDF.

    Docling is preferred for PDFs because it handles document layout and problematic
    text layers better than plain native extraction. If Docling is not available or
    fails for a document, the legacy PyMuPDF/PaddleOCR hybrid path is used as a
    fallback so uploads can continue.

    Args:
        file_path: Path to PDF file
        use_ocr_fallback: Enable OCR for pages with no extractable text

    Returns:
        ExtractionResult with text and metadata
    """
    from src.config.config import settings

    if settings.pdf_extractor.lower() == "vlm":
        vlm_result = await _extract_pdf_vlm(file_path)
        if vlm_result.success:
            return vlm_result

        logger.warning(
            "VLM PDF extraction failed for %s; falling back to PyMuPDF/OCR: %s",
            file_path,
            vlm_result.error,
        )
        fallback = await _extract_pdf_pymupdf(
            file_path,
            use_ocr_fallback=use_ocr_fallback,
            force_ocr_all=True,
        )
        fallback.metadata["fallback_from"] = "vlm"
        fallback.metadata["vlm_error"] = vlm_result.error
        return fallback

    if settings.pdf_extractor.lower() == "docling":
        docling_result = await _extract_pdf_docling(file_path)
        if docling_result.success:
            quality_report = _analyze_vietnamese_text_quality(
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
                "(score=%d, issues=%s); "
                "falling back to PyMuPDF/OCR",
                file_path,
                quality_report.score,
                ", ".join(quality_report.issues),
            )
            fallback = await _extract_pdf_pymupdf(
                file_path,
                use_ocr_fallback=use_ocr_fallback,
                force_ocr_all=True,
            )
            fallback.metadata["fallback_from"] = "docling"
            fallback.metadata["docling_error"] = (
                "Docling output failed Vietnamese quality gate: "
                + ", ".join(quality_report.issues)
            )
            fallback.metadata["docling_quality"] = asdict(quality_report)
            fallback.metadata["docling_chars"] = len(docling_result.text)
            return fallback

        logger.warning(
            "Docling PDF extraction failed for %s; falling back to PyMuPDF/OCR: %s",
            file_path,
            docling_result.error,
        )

        fallback = await _extract_pdf_pymupdf(
            file_path,
            use_ocr_fallback=use_ocr_fallback,
            force_ocr_all=True,
        )
        fallback.metadata["fallback_from"] = "docling"
        fallback.metadata["docling_error"] = docling_result.error
        return fallback

    return await _extract_pdf_pymupdf(file_path, use_ocr_fallback=use_ocr_fallback)


async def _extract_pdf_vlm(file_path: str) -> ExtractionResult:
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
                initial_quality = _analyze_vietnamese_text_quality(
                    cleaned_text,
                    lang=settings.ocr_lang,
                    fallback_score=settings.docling_quality_fallback_score,
                )
                should_verify = (
                    settings.vlm_page_verification_enabled
                    and (
                        not settings.vlm_verify_only_failed_pages
                        or initial_quality.should_fallback
                    )
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

                final_quality = _analyze_vietnamese_text_quality(
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
        page_texts = [
            (page["page_index"], page["canonical_text"])
            for page in processed_pages
        ]
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

        final_quality = _analyze_vietnamese_text_quality(
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


def _clean_vlm_markdown(text: str) -> str:
    """Light cleanup that removes model formatting artifacts without rewriting content."""
    cleaned = text.strip()
    cleaned = re.sub(r"^\s*```(?:markdown|md|text)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    cleaned = html.unescape(cleaned).replace("\xa0", " ")
    cleaned = re.sub(r"[ \t]{3,}", "  ", cleaned)
    cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)
    return cleaned.strip()


def _meaningful_coverage_ratio(source_text: str, final_text: str) -> float:
    """Estimate whether cleanup/verification dropped too much visible content."""
    source_count = _meaningful_char_count(source_text)
    if source_count == 0:
        return 1.0
    final_count = _meaningful_char_count(final_text)
    return round(final_count / source_count, 4)


def _meaningful_char_count(text: str) -> int:
    cleaned = html.unescape(text).replace("\xa0", " ")
    cleaned = re.sub(r"```(?:markdown|md|text)?|```", "", cleaned, flags=re.IGNORECASE)
    return sum(1 for char in cleaned if char.isalnum() or char in VIETNAMESE_DIACRITICS)


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
    from io import BytesIO
    from PIL import Image

    pages_dir = audit_dir / "pages"
    raw_dir = audit_dir / "raw"
    canonical_dir = audit_dir / "canonical"
    pages_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    canonical_dir.mkdir(parents=True, exist_ok=True)

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


def _prepare_vlm_image_data_url(image_bytes: bytes) -> str:
    """Resize and compress rendered page image before sending it to the VLM."""
    from io import BytesIO
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


async def _extract_pdf_docling(file_path: str) -> ExtractionResult:
    """Extract PDF text using Docling."""
    logger.info("Extracting PDF using Docling: %s", file_path)
    try:
        import fitz
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = await asyncio.to_thread(converter.convert, file_path)
        text = result.document.export_to_markdown()

        pages = 0
        try:
            doc = fitz.open(file_path)
            pages = len(doc)
            doc.close()
        except Exception:
            pages = 1

        return ExtractionResult(
            text=text,
            pages=pages,
            page_texts=[(0, text)] if text.strip() else [],
            metadata={
                "extractor": "docling",
                "engine": "docling",
                "ocr_used": True,
                "extraction_method": "docling",
            },
            success=bool(text.strip()),
        )
    except Exception as e:
        logger.error("Docling PDF extraction failed for %s: %s", file_path, e)
        return ExtractionResult(
            success=False,
            error=f"Docling PDF extraction failed: {e}",
        )


async def _extract_pdf_pymupdf(
    file_path: str,
    use_ocr_fallback: bool = True,
    force_ocr_all: bool = False,
) -> ExtractionResult:
    """Extract text from PDF using PyMuPDF with PaddleOCR fallback for scanned pages."""
    logger.info("Extracting PDF using PyMuPDF (native text): %s", file_path)
    try:
        import fitz
        from src.modules.document.infrastructure.ocr.ocr_client import get_ocr_client
        from src.config.config import settings

        doc = fitz.open(file_path)
        num_pages = len(doc)
        text_parts = []
        page_texts = []  # Track (page_num, text) for citation page tracking
        pages_needing_ocr = []
        ocr_lang = settings.ocr_lang

        # First pass: extract text with PyMuPDF
        for page_num, page in enumerate(doc):
            page_text = page.get_text()
            if force_ocr_all:
                text_parts.append(page_text)
                pages_needing_ocr.append(page_num)
                continue

            # If the page has text and it is of acceptable quality, keep it.
            # Otherwise, route the page to OCR.
            if page_text.strip() and not _is_low_quality_text(page_text, lang=ocr_lang):
                text_parts.append(page_text)
                page_texts.append((page_num, page_text))  # Track page number
            else:
                # Mark page for OCR - use placeholder
                text_parts.append("")  # Placeholder for OCR result
                pages_needing_ocr.append(page_num)

        # If all pages have text or OCR disabled, return early
        if not pages_needing_ocr or not use_ocr_fallback:
            doc.close()
            full_text = "\n\n".join([t for t in text_parts if t])
            return ExtractionResult(
                text=full_text,
                pages=num_pages,
                page_texts=page_texts,  # Include page tracking
                metadata={
                    "extractor": "pymupdf",
                    "engine": "fitz",
                    "ocr_used": False,
                    "extraction_method": "normal",
                },
                success=bool(full_text.strip()),
            )

        # Second pass: OCR for pages without text
        ocr_client = get_ocr_client()
        async with ocr_client:
            for page_num in pages_needing_ocr:
                page = doc[page_num]

                # Convert page to image
                mat = fitz.Matrix(3.0, 3.0)  # 3x zoom for better OCR
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")

                # Perform OCR
                ocr_result = await ocr_client.ocr_image_bytes(img_bytes)

                if ocr_result.success and ocr_result.text.strip():
                    # Update placeholder with OCR text
                    text_parts[page_num] = ocr_result.text
                    page_texts.append((page_num, ocr_result.text))  # Track OCR pages too
                elif text_parts[page_num].strip():
                    page_texts.append((page_num, text_parts[page_num]))

        doc.close()

        full_text = "\n\n".join([t for t in text_parts if t])

        return ExtractionResult(
            text=full_text,
            pages=num_pages,
            page_texts=page_texts,  # Include page tracking
            metadata={
                "extractor": "pymupdf-ocr-hybrid",
                "engine": "fitz",
                "ocr_used": True,
                "ocr_pages": len(pages_needing_ocr),
                "extraction_method": "ocr",
                "force_ocr_all": force_ocr_all,
            },
            success=bool(full_text.strip()),
        )

    except Exception as e:
        logger.error("PyMuPDF extraction failed for %s: %s", file_path, e)
        return ExtractionResult(
            success=False,
            error=f"PDF extraction failed: {e}",
        )


def extract_docx(file_path: str) -> ExtractionResult:
    """Extract text from DOCX using python-docx.

    Args:
        file_path: Path to DOCX file

    Returns:
        ExtractionResult with text and metadata
    """
    logger.info("Extracting DOCX using python-docx: %s", file_path)
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
            metadata={"extractor": "python-docx", "extraction_method": "normal", "ocr_used": False},
            success=bool(full_text.strip()),
        )
    except Exception as e:
        logger.error("DOCX extraction failed for %s: %s", file_path, e)
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
    logger.info("Extracting PPTX using python-pptx: %s", file_path)
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
            metadata={"extractor": "python-pptx", "extraction_method": "normal", "ocr_used": False},
            success=bool(full_text.strip()),
        )
    except Exception as e:
        logger.error("PPTX extraction failed for %s: %s", file_path, e)
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
        # Try with different encoding
        logger.warning("UTF-8 decoding failed for %s, falling back to latin-1", file_path)
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                text = f.read()
            return ExtractionResult(
                text=text,
                pages=1,
                metadata={"extractor": "native", "encoding": "latin-1", "extraction_method": "normal", "ocr_used": False},
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


async def extract_image_ocr(file_path: str) -> ExtractionResult:
    """Extract text from image using PaddleOCR service.

    Args:
        file_path: Path to image file

    Returns:
        ExtractionResult with text and metadata
    """
    try:
        from src.modules.document.infrastructure.ocr.ocr_client import get_ocr_client

        ocr_client = get_ocr_client()
        async with ocr_client:
            result = await ocr_client.ocr_file(file_path)

        if result.success:
            return ExtractionResult(
                text=result.text,
                pages=1,
                metadata={
                    "extractor": "paddleocr",
                    "confidence": result.confidence,
                },
                success=True,
            )
        else:
            # Fallback to Docling if PaddleOCR fails
            return await _extract_image_docling(file_path)

    except Exception as e:
        # Fallback to Docling on any error
        return await _extract_image_docling(file_path, error=str(e))




async def _extract_image_docling(file_path: str, error: str | None = None) -> ExtractionResult:
    """Fallback image extraction using Docling.

    Args:
        file_path: Path to image file
        error: Original error that triggered fallback

    Returns:
        ExtractionResult with text and metadata
    """
    logger.info("Extracting image using Docling OCR: %s", file_path)
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(file_path)

        text = result.document.export_to_markdown()

        return ExtractionResult(
            text=text,
            pages=1,
            metadata={"extractor": "docling-ocr", "fallback_from": "paddleocr"},
            success=bool(text.strip()),
        )
    except Exception as e:
        fallback_err = str(e)
        return ExtractionResult(
            success=False,
            error=f"Image OCR failed (PaddleOCR: {error}, Docling: {fallback_err})",
        )


async def extract_content(file_path: str, file_type: str) -> ExtractionResult:
    """Extract text from file using appropriate extractor.

    Args:
        file_path: Path to the file
        file_type: File extension (e.g., "pdf", "docx")

    Returns:
        ExtractionResult with text, pages, metadata
    """

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
            result = await extract_pdf(file_path)
        elif file_type == "docx":
            result = extract_docx(file_path)
        elif file_type == "pptx":
            result = extract_pptx(file_path)
        elif file_type in {"txt", "md"}:
            result = extract_text_file(file_path)
        elif file_type in OCR_TYPES:
            result = await extract_image_ocr(file_path)
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
            logger.info("Extraction successful. Method: %s, Pages: %d", result.metadata['extraction_method'], result.pages)
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


def extract_content_sync(file_path: str, file_type: str) -> ExtractionResult:
    """Synchronous wrapper for extract_content.

    This function runs the async extract_content in a new event loop.
    It's designed to be called from sync contexts (e.g., background tasks).

    Args:
        file_path: Path to the file
        file_type: File extension (e.g., "pdf", "docx")

    Returns:
        ExtractionResult with text, pages, metadata
    """
    return asyncio.run(extract_content(file_path, file_type))


__all__ = [
    "ExtractionResult",
    "extract_content",
    "extract_content_sync",
    "extract_pdf",
    "extract_docx",
    "extract_pptx",
    "extract_text_file",
    "extract_image_ocr",
    "_extract_image_docling",
]
