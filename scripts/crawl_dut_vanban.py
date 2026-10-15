"""Crawl DUT legal/regulation documents into docs_to_upload/.

The source page is paginated:
    https://dut.udn.vn/VanbanPhapquy
    https://dut.udn.vn/VanBanPhapQuy/page/2

Usage:
    python scripts/crawl_dut_vanban.py
    python scripts/crawl_dut_vanban.py --dry-run
    python scripts/crawl_dut_vanban.py --limit-pages 2 --overwrite
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


BASE_URL = "https://dut.udn.vn/VanbanPhapquy"
PAGE_URL = "https://dut.udn.vn/VanBanPhapQuy/page/{page}"
OUTPUT_DIR = "docs_to_upload"
MANIFEST_JSON = "_dut_vanban_manifest.json"
MANIFEST_CSV = "_dut_vanban_manifest.csv"
DOCUMENT_PATH_MARKER = "/Files/admin/files/VanbanPhapquy/"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
)
DOWNLOAD_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".rar",
}


@dataclass
class DocumentRecord:
    """One document found on the source site."""

    page: int
    document_id: str
    field: str
    title: str
    number: str
    issued_date: str
    effective_date: str
    issuer: str
    document_type: str
    status: str
    source_url: str
    filename: str
    local_path: str
    downloaded: bool = False
    skipped: bool = False
    error: str = ""


def fetch_text(url: str, timeout: int, user_agent: str) -> str:
    """Fetch HTML text from a URL."""
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return raw.decode("utf-8", errors="replace")


def download_file(url: str, destination: Path, timeout: int, user_agent: str) -> None:
    """Download one file to destination."""
    request = Request(url, headers={"User-Agent": user_agent, "Referer": BASE_URL})
    with urlopen(request, timeout=timeout) as response:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as output:
            while True:
                chunk = response.read(1024 * 128)
                if not chunk:
                    break
                output.write(chunk)


def partial_path(destination: Path) -> Path:
    """Return the temporary path used while a file is being downloaded."""
    return destination.with_name(f"{destination.name}.part")


def safe_url(url: str) -> str:
    """Percent-encode unsafe path characters while preserving query."""
    parts = urlsplit(url)
    path = quote(unquote(parts.path), safe="/:@")
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def clean_text(value: str) -> str:
    """Remove tags and collapse whitespace."""
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def sanitize_filename(name: str, max_length: int = 180) -> str:
    """Make a URL filename safe for local filesystems."""
    name = unquote(name).strip()
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name:
        name = "document"
    if len(name) > max_length:
        stem = Path(name).stem[: max_length - len(Path(name).suffix) - 1]
        name = f"{stem}{Path(name).suffix}"
    return name


def unique_path(path: Path) -> Path:
    """Return a non-existing variant of path."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for index in range(2, 10_000):
        candidate = parent / f"{stem} ({index}){suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Cannot find a unique filename for {path}")


def find_last_page(html: str) -> int:
    """Infer the last pagination page from pager links."""
    pages = [
        int(match)
        for match in re.findall(r"/VanBanPhapQuy/page/(\d+)", html, flags=re.I)
    ]
    return max(pages) if pages else 1


def document_url_from_row(row_html: str, page_url: str) -> str | None:
    """Extract a DUT document URL from a table row."""
    hrefs = re.findall(r"<a\b[^>]*href=['\"]([^'\"]+)['\"]", row_html, flags=re.I)
    for href in hrefs:
        absolute = urljoin(page_url, unescape(href))
        if DOCUMENT_PATH_MARKER.lower() not in absolute.lower():
            continue
        extension = Path(urlsplit(absolute).path).suffix.lower()
        if extension and extension not in DOWNLOAD_EXTENSIONS:
            continue
        return safe_url(absolute)
    return None


def parse_records(html: str, page: int, page_url: str, output_dir: Path) -> list[DocumentRecord]:
    """Parse document rows from one HTML page."""
    records: list[DocumentRecord] = []
    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", html, flags=re.I | re.S)

    for row_html in rows:
        source_url = document_url_from_row(row_html, page_url)
        if not source_url:
            continue

        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row_html, flags=re.I | re.S)
        values = [clean_text(cell) for cell in cells]
        if len(values) < 10:
            values = (values + [""] * 10)[:10]

        original_name = Path(unquote(urlsplit(source_url).path)).name
        filename = sanitize_filename(original_name)
        local_path = output_dir / filename

        records.append(
            DocumentRecord(
                page=page,
                document_id=values[0],
                field=values[1],
                title=values[2].replace(" New", "").strip(),
                number=values[3],
                issued_date=values[4],
                effective_date=values[5],
                issuer=values[6],
                document_type=values[7],
                status=values[8],
                source_url=source_url,
                filename=filename,
                local_path=str(local_path),
            )
        )

    return records


def deduplicate(records: Iterable[DocumentRecord]) -> list[DocumentRecord]:
    """Deduplicate records by source URL."""
    seen: set[str] = set()
    unique_records: list[DocumentRecord] = []
    for record in records:
        key = record.source_url.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_records.append(record)
    return unique_records


def write_manifest(records: list[DocumentRecord], output_dir: Path) -> None:
    """Write JSON and CSV manifests next to downloaded files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": BASE_URL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(records),
        "downloaded": sum(1 for record in records if record.downloaded),
        "skipped": sum(1 for record in records if record.skipped),
        "failed": sum(1 for record in records if record.error),
        "records": [asdict(record) for record in records],
    }
    (output_dir / MANIFEST_JSON).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = list(asdict(records[0]).keys()) if records else list(DocumentRecord.__annotations__)
    with (output_dir / MANIFEST_CSV).open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def crawl(args: argparse.Namespace) -> int:
    """Crawl pages and optionally download documents."""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    first_html = fetch_text(args.base_url, timeout=args.timeout, user_agent=args.user_agent)
    last_page = find_last_page(first_html)
    if args.limit_pages:
        last_page = min(last_page, args.limit_pages)

    print(f"Detected {last_page} page(s).")
    all_records = parse_records(first_html, page=1, page_url=args.base_url, output_dir=output_dir)

    for page in range(2, last_page + 1):
        page_url = PAGE_URL.format(page=page)
        try:
            html = fetch_text(page_url, timeout=args.timeout, user_agent=args.user_agent)
            page_records = parse_records(html, page=page, page_url=page_url, output_dir=output_dir)
            all_records.extend(page_records)
            print(f"Page {page}/{last_page}: found {len(page_records)} document(s).")
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"Page {page}/{last_page}: failed: {exc}")
        time.sleep(args.delay)

    records = deduplicate(all_records)
    print(f"Found {len(records)} unique document link(s).")

    if args.dry_run:
        for record in records:
            print(f"[DRY] {record.document_id} | {record.title} | {record.source_url}")
        write_manifest(records, output_dir)
        print(f"Dry-run manifest written to {output_dir / MANIFEST_JSON}")
        return 0

    for index, record in enumerate(records, start=1):
        destination = Path(record.local_path)
        if destination.exists() and not args.overwrite:
            record.skipped = True
            print(f"[{index}/{len(records)}] skip existing: {destination.name}", flush=True)
            continue

        if not args.overwrite:
            destination = unique_path(destination)
            record.local_path = str(destination)
            record.filename = destination.name

        temporary_destination = partial_path(destination)
        if temporary_destination.exists():
            temporary_destination.unlink()

        for attempt in range(1, args.retries + 1):
            try:
                download_file(
                    record.source_url,
                    destination=temporary_destination,
                    timeout=args.timeout,
                    user_agent=args.user_agent,
                )
                temporary_destination.replace(destination)
                record.downloaded = True
                print(f"[{index}/{len(records)}] downloaded: {destination.name}", flush=True)
                break
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                record.error = str(exc)
                if temporary_destination.exists():
                    temporary_destination.unlink()
                if attempt >= args.retries:
                    print(f"[{index}/{len(records)}] failed: {destination.name}: {exc}", flush=True)
                else:
                    time.sleep(args.delay * attempt)

        time.sleep(args.delay)

    write_manifest(records, output_dir)
    print(f"Manifest written to {output_dir / MANIFEST_JSON}")
    print(f"CSV written to {output_dir / MANIFEST_CSV}")
    return 1 if any(record.error for record in records) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crawl and download all DUT VanBanPhapQuy documents.",
    )
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    parser.add_argument("--limit-pages", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--delay", type=float, default=0.4)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return crawl(args)


if __name__ == "__main__":
    raise SystemExit(main())
