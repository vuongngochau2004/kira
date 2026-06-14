"""Debug document extraction using the project's real processing path.

By default this script runs the same extractor path used by document ingestion:
the configured PDF extractor, quality gates, and fallback chain. Use
``--mode page-ocr`` to run the older per-page OCR/native debug.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.config import settings  # noqa: E402
from src.modules.document.domain.services.extractor import (  # noqa: E402
    _analyze_vietnamese_text_quality,
    _is_low_quality_text,
    extract_content,
)
from src.modules.document.infrastructure.ocr.ocr_client import get_ocr_client  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export document extraction outputs for inspection.",
    )
    parser.add_argument("documents", nargs="+")
    parser.add_argument("--output-dir", default="reports/ocr_debug")
    parser.add_argument(
        "--mode",
        choices=["pipeline", "page-ocr"],
        default="pipeline",
        help="pipeline runs the project extractor; page-ocr exports per-page OCR/native debug.",
    )
    parser.add_argument("--pages", default="1-2", help="1-based pages, e.g. 1,3,5 or 1-3")
    parser.add_argument("--zoom", type=float, default=3.0)
    parser.add_argument("--lang", default=None)
    return parser


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")
    return slug[:100] or "document"


def parse_pages(spec: str, total_pages: int) -> list[int]:
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            pages.update(range(start, end + 1))
        else:
            pages.add(int(part))
    return [page - 1 for page in sorted(pages) if 1 <= page <= total_pages]


def get_file_type(path: Path) -> str:
    return path.suffix.lower().lstrip(".") or "txt"


async def debug_pipeline(document_path: Path, output_root: Path, lang: str | None) -> None:
    """Run the same extraction path used by the ingestion pipeline."""
    doc_dir = output_root / slugify(document_path.stem)
    doc_dir.mkdir(parents=True, exist_ok=True)
    file_type = get_file_type(document_path)
    ocr_lang = lang or settings.ocr_lang

    start = time.perf_counter()
    result = await extract_content(str(document_path), file_type)
    elapsed = time.perf_counter() - start

    text = result.text or ""
    quality_report = _analyze_vietnamese_text_quality(
        text,
        lang=ocr_lang,
        fallback_score=settings.docling_quality_fallback_score,
    )

    processed_path = doc_dir / "processed_text.md"
    metadata_path = doc_dir / "metadata.json"
    quality_path = doc_dir / "quality.json"
    summary_path = doc_dir / "summary.md"

    processed_path.write_text(text, encoding="utf-8")
    metadata_path.write_text(
        json.dumps(result.metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    quality_path.write_text(
        json.dumps(asdict(quality_report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = [
        f"# Pipeline Debug: {document_path.name}",
        "",
        f"- Mode: `pipeline`",
        f"- File type: `{file_type}`",
        f"- Success: `{result.success}`",
        f"- Error: `{result.error or ''}`",
        f"- Elapsed seconds: `{elapsed:.2f}`",
        f"- Pages: `{result.pages}`",
        f"- Output chars: `{len(text)}`",
        f"- Extractor: `{result.metadata.get('extractor', '')}`",
        f"- Extraction method: `{result.metadata.get('extraction_method', '')}`",
        f"- OCR used: `{result.metadata.get('ocr_used', False)}`",
        f"- OCR pages: `{result.metadata.get('ocr_pages', '')}`",
        f"- Fallback from: `{result.metadata.get('fallback_from', '')}`",
        f"- Force OCR all: `{result.metadata.get('force_ocr_all', False)}`",
        f"- VLM model: `{result.metadata.get('model', '')}`",
        f"- Render DPI: `{result.metadata.get('render_dpi', '')}`",
        f"- Page concurrency: `{result.metadata.get('page_concurrency', '')}`",
        f"- Verify only failed pages: `{result.metadata.get('verify_only_failed_pages', '')}`",
        f"- Canonicalization: `{result.metadata.get('canonicalization', {})}`",
        f"- Quality status: `{result.metadata.get('quality_status', '')}`",
        f"- Page warnings: `{result.metadata.get('page_warnings', [])}`",
        f"- Audit path: `{result.metadata.get('audit_path', '')}`",
        f"- Docling quality score: `{result.metadata.get('docling_quality', {}).get('score', '')}`",
        f"- Docling quality issues: `{', '.join(result.metadata.get('docling_quality', {}).get('issues', []))}`",
        f"- Final quality score: `{quality_report.score}`",
        f"- Final quality issues: `{', '.join(quality_report.issues)}`",
        "",
        "## Files",
        "",
        f"- Processed text: `{processed_path.name}`",
        f"- Metadata: `{metadata_path.name}`",
        f"- Final quality: `{quality_path.name}`",
        "",
        "## Preview",
        "",
        "```text",
        text[:3000],
        "```",
        "",
    ]
    summary_path.write_text("\n".join(summary), encoding="utf-8")
    print(f"Wrote pipeline debug output: {doc_dir}")


def draw_overlay(image_bytes: bytes, raw_response: dict[str, Any] | None) -> bytes:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)
    lines = (raw_response or {}).get("lines") or []

    for line in lines:
        if not isinstance(line, dict):
            continue
        box = line.get("box")
        text = str(line.get("text") or "")
        if not box or len(box) != 4:
            continue
        points = [(float(point[0]), float(point[1])) for point in box]
        draw.line(points + [points[0]], fill=(255, 0, 0), width=3)
        x = min(point[0] for point in points)
        y = min(point[1] for point in points)
        if text:
            draw.text((x, max(0, y - 14)), text[:40], fill=(0, 0, 255))

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


async def debug_pdf(pdf_path: Path, output_root: Path, pages_spec: str, zoom: float, lang: str | None) -> None:
    import fitz

    doc = fitz.open(pdf_path)
    page_indexes = parse_pages(pages_spec, len(doc))
    doc_dir = output_root / slugify(pdf_path.stem)
    doc_dir.mkdir(parents=True, exist_ok=True)

    combined_ocr: list[str] = []
    combined_native: list[str] = []
    summary: list[str] = [
        f"# OCR Debug: {pdf_path.name}",
        "",
        f"- OCR_BASE_URL: `{settings.ocr_base_url}`",
        f"- OCR_LANG: `{lang or settings.ocr_lang}`",
        f"- Pages tested: {', '.join(str(index + 1) for index in page_indexes)}",
        "",
    ]

    ocr_client = get_ocr_client()
    async with ocr_client:
        for page_index in page_indexes:
            page = doc[page_index]
            native_text = page.get_text() or ""
            low_quality = _is_low_quality_text(native_text, lang=lang or settings.ocr_lang)

            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            image_bytes = pix.tobytes("png")

            image_path = doc_dir / f"page_{page_index + 1:03d}.png"
            overlay_path = doc_dir / f"page_{page_index + 1:03d}_ocr_overlay.png"
            native_path = doc_dir / f"page_{page_index + 1:03d}_native.txt"
            ocr_path = doc_dir / f"page_{page_index + 1:03d}_ocr.txt"
            raw_path = doc_dir / f"page_{page_index + 1:03d}_ocr_raw.json"

            image_path.write_bytes(image_bytes)
            native_path.write_text(native_text, encoding="utf-8")
            combined_native.append(f"\n\n===== PAGE {page_index + 1} =====\n{native_text}")

            result = await ocr_client.ocr_image_bytes(image_bytes, lang=lang)
            ocr_text = result.text if result.success else f"OCR FAILED: {result.error}"
            ocr_path.write_text(ocr_text, encoding="utf-8")
            raw_path.write_text(
                json.dumps(result.raw_response or {"error": result.error}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            combined_ocr.append(f"\n\n===== PAGE {page_index + 1} =====\n{ocr_text}")

            overlay_path.write_bytes(draw_overlay(image_bytes, result.raw_response))

            summary.extend(
                [
                    f"## Page {page_index + 1}",
                    "",
                    f"- Image: `{image_path.name}`",
                    f"- OCR overlay: `{overlay_path.name}`",
                    f"- Native text: `{native_path.name}`",
                    f"- OCR text: `{ocr_path.name}`",
                    f"- Native low quality: `{low_quality}`",
                    f"- OCR success: `{result.success}`",
                    f"- OCR confidence: `{result.confidence:.4f}`",
                    f"- Native chars: {len(native_text)}",
                    f"- OCR chars: {len(ocr_text)}",
                    "",
                ]
            )

    doc.close()
    (doc_dir / "native_all.txt").write_text("".join(combined_native).strip(), encoding="utf-8")
    (doc_dir / "ocr_all.txt").write_text("".join(combined_ocr).strip(), encoding="utf-8")
    (doc_dir / "summary.md").write_text("\n".join(summary), encoding="utf-8")
    print(f"Wrote OCR debug output: {doc_dir}")


async def main_async() -> int:
    log_level = logging.DEBUG if os.getenv("DEBUG", "").lower() == "true" else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args = build_parser().parse_args()
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    for document in args.documents:
        document_path = Path(document)
        if args.mode == "pipeline":
            await debug_pipeline(document_path, output_root, args.lang)
        else:
            if get_file_type(document_path) != "pdf":
                print(f"Skipping non-PDF for page OCR mode: {document_path}", file=sys.stderr)
                continue
            await debug_pdf(document_path, output_root, args.pages, args.zoom, args.lang)

    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
