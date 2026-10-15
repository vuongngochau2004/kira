"""Bulk upload local documents through the app's public upload API.

This intentionally uses the same endpoint as the UI:
    POST /api/v1/documents/upload

That means OCR, cleaning, chunking, embedding, DB persistence, and Qdrant
indexing all happen through the normal production pipeline.
"""

from __future__ import annotations

import argparse
import mimetypes
import time
from pathlib import Path

import httpx


DEFAULT_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".md"}


def iter_files(input_dir: Path, extensions: set[str]) -> list[Path]:
    """Return uploadable files sorted by name."""
    return sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in extensions
        and not path.name.startswith("_")
        and not path.name.endswith(".part")
    )


def upload(args: argparse.Namespace) -> int:
    input_dir = Path(args.input_dir)
    files = iter_files(input_dir, {ext.lower() for ext in args.extensions})
    if args.limit:
        files = files[: args.limit]

    if not files:
        print(f"No uploadable files found in {input_dir}")
        return 1

    headers = {"Authorization": f"Bearer {args.token}"}
    uploaded = 0
    failed = 0

    with httpx.Client(timeout=args.timeout) as client:
        for index, path in enumerate(files, start=1):
            media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            print(f"[{index}/{len(files)}] uploading: {path.name}", flush=True)

            try:
                with path.open("rb") as file:
                    response = client.post(
                        f"{args.base_url.rstrip('/')}/api/v1/documents/upload",
                        headers=headers,
                        files={"file": (path.name, file, media_type)},
                    )
                if response.status_code >= 400:
                    failed += 1
                    print(f"  failed {response.status_code}: {response.text[:500]}", flush=True)
                else:
                    uploaded += 1
                    data = response.json()
                    print(
                        f"  uploaded document_id={data.get('id')} status={data.get('status')}",
                        flush=True,
                    )
            except Exception as exc:
                failed += 1
                print(f"  failed: {exc}", flush=True)

            time.sleep(args.delay)

    print(f"Done. uploaded={uploaded}, failed={failed}")
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bulk upload docs through KIRA upload API.")
    parser.add_argument("--input-dir", default="docs_to_upload")
    parser.add_argument("--base-url", default="http://localhost:8006")
    parser.add_argument("--token", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--extensions", nargs="+", default=sorted(DEFAULT_EXTENSIONS))
    return parser


def main() -> int:
    return upload(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
