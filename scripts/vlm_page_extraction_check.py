"""Test the VLM page extraction pipeline on a single local PDF.

Renders selected pages to PNG images, then transcribes each image through the
production Ollama VLM path (the same helpers used by the document ingestion
pipeline) and writes both artifacts to disk so they can be inspected side by
side. Optional second-pass verification mirrors the production verify step.

Outputs (under --output-dir):
    page_NNN.png               - rendered page image (full DPI)
    page_NNN_vlm.md            - VLM transcription (cleaned)
    page_NNN_vlm_verified.md   - VLM verify pass (only with --verify)
    summary.json               - per-page metadata, timing, quality report

Example:
    .venv/bin/python scripts/test_vlm_page_extraction.py \
        --input "path/to/doc.pdf" \
        --pages 1,3,5-7 \
        --verify
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.config import settings  # noqa: E402
from src.modules.document.domain.services.extractor import (  # noqa: E402
    _analyze_vietnamese_text_quality,
    _clean_vlm_markdown,
    _prepare_vlm_image_data_url,
    _transcribe_page_with_ollama_vlm,
    _verify_page_with_ollama_vlm,
)


def parse_pages(spec: str, total_pages: int) -> list[int]:
    """Parse a 1-based page spec into a sorted, validated list of 0-based indices.

    Supports comma lists and ranges: "1", "1,3,5", "2-4", "1,3-5,8".
    """
    if not spec.strip():
        raise ValueError("empty page spec")

    indices: set[int] = set()
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start_s, end_s = token.split("-", 1)
            start = int(start_s)
            end = int(end_s)
            if start > end:
                raise ValueError(f"invalid range '{token}': start > end")
            for page_num in range(start, end + 1):
                indices.add(_to_index(page_num, total_pages, token))
        else:
            page_num = int(token)
            indices.add(_to_index(page_num, total_pages, token))

    return sorted(indices)


def _to_index(page_num: int, total_pages: int, token: str) -> int:
    """Convert a 1-based page number to a 0-based index with bounds checks."""
    if page_num < 1:
        raise ValueError(f"invalid page '{token}': pages are 1-based")
    index = page_num - 1
    if index >= total_pages:
        raise ValueError(f"page {page_num} out of range (PDF has {total_pages} pages)")
    return index


def slugify(path: Path) -> str:
    """Build a filesystem-safe slug from a file stem."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", path.stem).strip("_")
    return slug[:80] or "document"


async def render_page(file_path: str, page_index: int, dpi: int) -> bytes:
    """Render one PDF page (0-based index) to PNG bytes at the given DPI."""
    import fitz

    doc = fitz.open(file_path)
    try:
        page = doc[page_index]
        zoom = dpi / 72
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()


async def process_page(
    *,
    file_path: str,
    page_index: int,
    dpi: int,
    output_dir: Path,
    verify: bool,
) -> dict[str, Any]:
    """Render, transcribe, and optionally verify one page; write artifacts to disk."""
    page_number = page_index + 1
    started = time.perf_counter()

    # 1. Render the page to a full-resolution PNG (the human-facing image).
    png_bytes = await render_page(file_path, page_index, dpi)
    image_name = f"page_{page_number:03d}.png"
    image_path = output_dir / image_name
    image_path.write_bytes(png_bytes)

    # 2. Prepare a compressed data URL for the VLM (resize + JPEG, per settings).
    image_data_url = _prepare_vlm_image_data_url(png_bytes)

    # 3. Transcribe via the production Ollama VLM path.
    raw_text = await _transcribe_page_with_ollama_vlm(
        image_data_url=image_data_url,
        page_number=page_number,
    )
    transcription = _clean_vlm_markdown(raw_text)
    vlm_path = output_dir / f"page_{page_number:03d}_vlm.md"
    vlm_path.write_text(transcription, encoding="utf-8")

    record: dict[str, Any] = {
        "page_number": page_number,
        "page_index": page_index,
        "image": image_name,
        "vlm_transcription": vlm_path.name,
        "vlm_chars": len(transcription),
        "vlm_words": len(transcription.split()),
        "quality": asdict(
            _analyze_vietnamese_text_quality(
                transcription,
                lang=settings.ocr_lang,
                fallback_score=settings.docling_quality_fallback_score,
            )
        ),
    }

    # 4. Optional verify pass against the source image.
    if verify:
        verified_raw = await _verify_page_with_ollama_vlm(
            image_data_url=image_data_url,
            page_number=page_number,
            transcription_text=transcription,
        )
        verified = _clean_vlm_markdown(verified_raw)
        verified_path = output_dir / f"page_{page_number:03d}_vlm_verified.md"
        verified_path.write_text(verified, encoding="utf-8")
        record["vlm_verified"] = verified_path.name
        record["vlm_verified_chars"] = len(verified)

    record["elapsed_seconds"] = round(time.perf_counter() - started, 2)
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Test the VLM page extraction pipeline on a local PDF.",
    )
    parser.add_argument("--input", required=True, help="Path to the source PDF file.")
    parser.add_argument(
        "--pages",
        default="1",
        help="1-based page spec, e.g. '1', '1,3,5', '2-4'. Default: first page.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory. Defaults to data/vlm_test/<filename-slug>.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=None,
        help=f"Render DPI (default: {settings.pdf_render_dpi}).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"Override Ollama VLM model (default: {settings.ollama_model}).",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Also run the production verify pass and save its output.",
    )
    return parser


async def run(args: argparse.Namespace) -> int:
    file_path = Path(args.input).expanduser().resolve()
    if not file_path.is_file():
        print(f"[ERROR] File not found: {file_path}")
        return 2
    if file_path.suffix.lower() != ".pdf":
        print(f"[ERROR] Only PDF inputs are supported, got: {file_path.suffix}")
        return 2

    # Apply model override into settings so the shared VLM helpers pick it up.
    if args.model:
        settings.ollama_model = args.model
    dpi = args.dpi if args.dpi is not None else settings.pdf_render_dpi

    if not settings.ollama_api_keys.strip():
        print("[ERROR] OLLAMA_API_KEYS is empty; VLM transcription requires it.")
        return 3

    # Probe page count up front so --pages can be validated.
    import fitz

    with fitz.open(str(file_path)) as doc:
        total_pages = len(doc)
    page_indices = parse_pages(args.pages, total_pages)

    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else PROJECT_ROOT / "data" / "vlm_test" / slugify(file_path)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[VLM-TEST] file={file_path.name} pages_total={total_pages}")
    print(f"[VLM-TEST] target_pages={[idx + 1 for idx in page_indices]} dpi={dpi}")
    print(f"[VLM-TEST] model={settings.ollama_model} verify={args.verify}")
    print(f"[VLM-TEST] output_dir={output_dir}")

    page_records: list[dict[str, Any]] = []
    for page_index in page_indices:
        print(f"[VLM-TEST] -> page {page_index + 1}/{total_pages} ...", flush=True)
        try:
            record = await process_page(
                file_path=str(file_path),
                page_index=page_index,
                dpi=dpi,
                output_dir=output_dir,
                verify=args.verify,
            )
        except Exception as exc:  # noqa: BLE001 - surface per-page failure, keep going
            print(f"[VLM-TEST]    page {page_index + 1} FAILED: {type(exc).__name__}: {exc}")
            page_records.append(
                {
                    "page_number": page_index + 1,
                    "page_index": page_index,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        print(
            f"[VLM-TEST]    page {record['page_number']}: "
            f"chars={record['vlm_chars']} words={record['vlm_words']} "
            f"elapsed={record['elapsed_seconds']}s"
        )
        page_records.append(record)

    summary = {
        "source_file": str(file_path),
        "model": settings.ollama_model,
        "dpi": dpi,
        "verify": args.verify,
        "total_pages_in_pdf": total_pages,
        "processed_pages": [idx + 1 for idx in page_indices],
        "pages": page_records,
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[VLM-TEST] summary written: {summary_path}")
    print(f"[VLM-TEST] done. {len(page_records)} page(s) processed.")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
