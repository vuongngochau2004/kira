"""Compare Docling, native PDF text, and PaddleOCR quality signals.

This script is for threshold tuning. It does not write to the database or vector
store; it only exports diagnostics that can be manually inspected.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.config import settings  # noqa: E402
from src.modules.document.domain.services.extractor import (  # noqa: E402
    _analyze_vietnamese_text_quality,
    _extract_pdf_docling,
)
from src.modules.document.infrastructure.ocr.ocr_client import get_ocr_client  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate extraction quality signals for PDF samples.",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="PDF files or directories containing PDF files.",
    )
    parser.add_argument("--output-dir", default="reports/extraction_quality")
    parser.add_argument("--pages", default="1-2", help="1-based pages, e.g. 1,3,5 or 1-3")
    parser.add_argument("--zoom", type=float, default=3.0)
    parser.add_argument("--lang", default=None)
    parser.add_argument(
        "--fallback-score",
        type=int,
        default=None,
        help="Quality score threshold that would trigger OCR fallback.",
    )
    parser.add_argument(
        "--skip-ocr",
        action="store_true",
        help="Only evaluate Docling and native PDF text.",
    )
    return parser


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")
    return slug[:100] or "document"


def collect_pdfs(inputs: list[str]) -> list[Path]:
    pdfs: list[Path] = []
    for item in inputs:
        path = Path(item)
        if path.is_dir():
            pdfs.extend(sorted(path.glob("*.PDF")))
            pdfs.extend(sorted(path.glob("*.pdf")))
        elif path.is_file():
            pdfs.append(path)
    return sorted(set(pdfs), key=lambda p: p.name.lower())


def parse_pages(spec: str, total_pages: int) -> list[int]:
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            pages.update(range(int(start_text), int(end_text) + 1))
        else:
            pages.add(int(part))
    return [page - 1 for page in sorted(pages) if 1 <= page <= total_pages]


def quality_row(
    *,
    pdf_name: str,
    source: str,
    page: int | None,
    text: str,
    elapsed_sec: float | None,
    success: bool,
    error: str | None,
    lang: str,
    fallback_score: int,
) -> dict:
    report = _analyze_vietnamese_text_quality(
        text,
        lang=lang,
        fallback_score=fallback_score,
    )
    data = asdict(report)
    return {
        "file": pdf_name,
        "source": source,
        "page": page or "",
        "success": success,
        "elapsed_sec": "" if elapsed_sec is None else round(elapsed_sec, 2),
        "error": error or "",
        "preview": text[:240].replace("\n", " "),
        "issues": ",".join(data.pop("issues")),
        **data,
    }


async def evaluate_pdf(
    pdf_path: Path,
    output_dir: Path,
    pages_spec: str,
    zoom: float,
    lang: str,
    fallback_score: int,
    skip_ocr: bool,
) -> list[dict]:
    import fitz

    rows: list[dict] = []
    doc_dir = output_dir / slugify(pdf_path.stem)
    doc_dir.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
    docling_result = await _extract_pdf_docling(str(pdf_path))
    elapsed = time.perf_counter() - start
    docling_text = docling_result.text if docling_result.success else ""
    (doc_dir / "docling.md").write_text(docling_text, encoding="utf-8")
    rows.append(
        quality_row(
            pdf_name=pdf_path.name,
            source="docling",
            page=None,
            text=docling_text,
            elapsed_sec=elapsed,
            success=docling_result.success,
            error=docling_result.error,
            lang=lang,
            fallback_score=fallback_score,
        )
    )

    doc = fitz.open(pdf_path)
    page_indexes = parse_pages(pages_spec, len(doc))
    ocr_client = get_ocr_client()
    if not skip_ocr:
        await ocr_client.__aenter__()

    try:
        for page_index in page_indexes:
            page = doc[page_index]
            page_number = page_index + 1
            native_text = page.get_text() or ""
            (doc_dir / f"page_{page_number:03d}_native.txt").write_text(
                native_text,
                encoding="utf-8",
            )
            rows.append(
                quality_row(
                    pdf_name=pdf_path.name,
                    source="native",
                    page=page_number,
                    text=native_text,
                    elapsed_sec=None,
                    success=bool(native_text.strip()),
                    error=None if native_text.strip() else "empty native text",
                    lang=lang,
                    fallback_score=fallback_score,
                )
            )

            if skip_ocr:
                continue

            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            image_bytes = pix.tobytes("png")
            start = time.perf_counter()
            ocr_result = await ocr_client.ocr_image_bytes(image_bytes, lang=lang)
            elapsed = time.perf_counter() - start
            ocr_text = ocr_result.text if ocr_result.success else ""
            (doc_dir / f"page_{page_number:03d}_paddleocr.txt").write_text(
                ocr_text,
                encoding="utf-8",
            )
            rows.append(
                quality_row(
                    pdf_name=pdf_path.name,
                    source="paddleocr",
                    page=page_number,
                    text=ocr_text,
                    elapsed_sec=elapsed,
                    success=ocr_result.success,
                    error=ocr_result.error,
                    lang=lang,
                    fallback_score=fallback_score,
                )
            )
    finally:
        if not skip_ocr:
            await ocr_client.__aexit__(None, None, None)
        doc.close()

    return rows


def write_outputs(rows: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    columns = [
        "file",
        "source",
        "page",
        "success",
        "elapsed_sec",
        "score",
        "should_fallback",
        "issues",
        "char_count",
        "word_count",
        "letter_count",
        "vi_diacritic_ratio",
        "unaccented_signal_ratio",
        "mojibake_count",
        "html_entity_count",
        "alphanumeric_artifact_ratio",
        "error",
        "preview",
    ]

    csv_path = output_dir / "quality_report.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    jsonl_path = output_dir / "quality_report.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary_lines = [
        "# Extraction Quality Report",
        "",
        f"- Rows: {len(rows)}",
        f"- CSV: `{csv_path.name}`",
        f"- JSONL: `{jsonl_path.name}`",
        "",
        "| File | Source | Page | Success | Score | Fallback | Issues | Preview |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        preview = row["preview"].replace("|", "\\|")
        if len(preview) > 120:
            preview = preview[:117] + "..."
        summary_lines.append(
            "| {file} | {source} | {page} | {success} | {score} | {should_fallback} | "
            "{issues} | {preview} |".format(**{**row, "preview": preview})
        )
    (output_dir / "summary.md").write_text("\n".join(summary_lines), encoding="utf-8")


async def main_async() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    lang = args.lang or settings.ocr_lang
    fallback_score = args.fallback_score or settings.docling_quality_fallback_score
    pdfs = collect_pdfs(args.inputs)
    if not pdfs:
        print("No PDF files found.", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for pdf_path in pdfs:
        print(f"Evaluating {pdf_path}")
        rows.extend(
            await evaluate_pdf(
                pdf_path=pdf_path,
                output_dir=output_dir,
                pages_spec=args.pages,
                zoom=args.zoom,
                lang=lang,
                fallback_score=fallback_score,
                skip_ocr=args.skip_ocr,
            )
        )

    write_outputs(rows, output_dir)
    print(f"Wrote quality report: {output_dir / 'summary.md'}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
