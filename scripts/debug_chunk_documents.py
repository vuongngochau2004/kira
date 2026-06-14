"""Export extraction and chunking outputs for a set of documents."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.modules.document.domain.services.chunker import chunk_document  # noqa: E402
from src.modules.document.domain.services.cleaner import clean_document  # noqa: E402
from src.modules.document.domain.services.extractor import extract_content  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run extract -> clean -> chunk and save debug artifacts.",
    )
    parser.add_argument("inputs", nargs="+", help="Files or directories to process.")
    parser.add_argument("--output-dir", default="reports/chunk_debug")
    parser.add_argument("--glob", default="*.PDF", help="Glob used when an input is a directory.")
    parser.add_argument("--document-id-prefix", default="debug")
    return parser


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")
    return slug[:120] or "document"


def collect_documents(inputs: list[str], glob_pattern: str) -> list[Path]:
    documents: list[Path] = []
    for input_value in inputs:
        path = Path(input_value)
        if path.is_dir():
            documents.extend(sorted(p for p in path.glob(glob_pattern) if p.is_file()))
        elif path.is_file():
            documents.append(path)
        else:
            print(f"Skipping missing input: {path}", file=sys.stderr)
    return documents


def file_type(path: Path) -> str:
    return path.suffix.lower().lstrip(".") or "txt"


def write_chunk_outputs(
    doc_dir: Path,
    source_path: Path,
    document_id: str,
    raw_text: str,
    cleaned_text: str,
    chunks: list,
    extraction_metadata: dict,
    elapsed_seconds: float,
) -> None:
    doc_dir.mkdir(parents=True, exist_ok=True)

    (doc_dir / "processed_text.md").write_text(raw_text, encoding="utf-8")
    (doc_dir / "cleaned_text.md").write_text(cleaned_text, encoding="utf-8")
    (doc_dir / "metadata.json").write_text(
        json.dumps(extraction_metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    chunk_records = [
        {
            "index": chunk.index,
            "token_count": chunk.token_count,
            "metadata": chunk.metadata,
            "content": chunk.content,
        }
        for chunk in chunks
    ]
    (doc_dir / "chunks.json").write_text(
        json.dumps(chunk_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for chunk in chunks:
        (doc_dir / f"chunk_{chunk.index:03d}.md").write_text(
            chunk.content,
            encoding="utf-8",
        )

    summary = [
        f"# Chunk Debug: {source_path.name}",
        "",
        f"- Document ID: `{document_id}`",
        f"- File type: `{file_type(source_path)}`",
        f"- Elapsed seconds: `{elapsed_seconds:.2f}`",
        f"- Extractor: `{extraction_metadata.get('extractor', '')}`",
        f"- Extraction method: `{extraction_metadata.get('extraction_method', '')}`",
        f"- OCR used: `{extraction_metadata.get('ocr_used', False)}`",
        f"- Pages: `{extraction_metadata.get('pages', '')}`",
        f"- Raw chars: `{len(raw_text)}`",
        f"- Cleaned chars: `{len(cleaned_text)}`",
        f"- Chunk count: `{len(chunks)}`",
        "",
        "## Chunks",
        "",
    ]
    for chunk in chunks:
        summary.extend(
            [
                f"### Chunk {chunk.index}",
                "",
                f"- Tokens: `{chunk.token_count}`",
                f"- Metadata: `{json.dumps(chunk.metadata, ensure_ascii=False)}`",
                "",
                "```text",
                chunk.content[:1200],
                "```",
                "",
            ]
        )
    (doc_dir / "summary.md").write_text("\n".join(summary), encoding="utf-8")


async def process_document(path: Path, output_root: Path, document_id_prefix: str) -> dict:
    started = time.perf_counter()
    doc_id = f"{document_id_prefix}-{slugify(path.stem)}"
    doc_dir = output_root / slugify(path.stem)

    result = await extract_content(str(path), file_type(path))
    elapsed = time.perf_counter() - started
    if not result.success:
        doc_dir.mkdir(parents=True, exist_ok=True)
        error_record = {
            "source": str(path),
            "success": False,
            "error": result.error,
            "elapsed_seconds": round(elapsed, 2),
            "metadata": result.metadata,
        }
        (doc_dir / "error.json").write_text(
            json.dumps(error_record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return error_record

    raw_text = result.text or ""
    cleaned_text = clean_document(raw_text)
    chunks = chunk_document(cleaned_text, document_id=doc_id)
    metadata = {**result.metadata, "pages": result.pages}
    write_chunk_outputs(
        doc_dir=doc_dir,
        source_path=path,
        document_id=doc_id,
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        chunks=chunks,
        extraction_metadata=metadata,
        elapsed_seconds=elapsed,
    )

    return {
        "source": str(path),
        "output_dir": str(doc_dir),
        "success": True,
        "elapsed_seconds": round(elapsed, 2),
        "extractor": result.metadata.get("extractor"),
        "extraction_method": result.metadata.get("extraction_method"),
        "ocr_used": result.metadata.get("ocr_used", False),
        "pages": result.pages,
        "raw_chars": len(raw_text),
        "cleaned_chars": len(cleaned_text),
        "chunk_count": len(chunks),
    }


async def main_async() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = build_parser().parse_args()
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    documents = collect_documents(args.inputs, args.glob)
    if not documents:
        print("No documents found.", file=sys.stderr)
        return 1

    records = []
    for index, document in enumerate(documents, start=1):
        print(f"[{index}/{len(documents)}] Processing {document}")
        records.append(await process_document(document, output_root, args.document_id_prefix))

    (output_root / "run_summary.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote chunk debug output: {output_root}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
