"""Admin-only HTTP entry points for pipeline stage demos."""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from kira.auth.dependencies import require_admin
from kira.auth.rate_limit import limit_user_requests
from kira.db.models import User
from kira.pipeline_lab.schemas import ClassifyRequest, RerankRequest
from kira.pipeline_lab.service import (
    inspect_classification,
    inspect_document,
    inspect_reranking,
)

router = APIRouter()
limit_debug = limit_user_requests("pipeline-lab", maximum=30, window_seconds=3600)
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
READ_BYTES = 1024 * 1024
SIGNATURES = {
    "pdf": b"%PDF-",
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
}


async def _read_document(file: UploadFile) -> tuple[str, bytes]:
    """Bound and validate a demo file before invoking an extractor."""
    suffix = (file.filename or "").rsplit(".", 1)[-1].lower()
    if suffix not in SIGNATURES:
        raise HTTPException(status_code=400, detail="Upload a PDF, PNG, or JPEG file")
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(READ_BYTES):
        size += len(chunk)
        if size > MAX_DOCUMENT_BYTES:
            raise HTTPException(status_code=413, detail="File exceeds the 10 MiB demo limit")
        chunks.append(chunk)
    content = b"".join(chunks)
    if not content.startswith(SIGNATURES[suffix]):
        raise HTTPException(status_code=400, detail="File content does not match its extension")
    return suffix, content


@router.post("/extract")
async def demo_extraction(
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
    __: None = Depends(limit_debug),
) -> dict[str, Any]:
    """Show OCR or configured PDF extraction output for an uploaded file."""
    suffix, content = await _read_document(file)
    return await inspect_document(content, suffix)


@router.post("/classify")
async def demo_classification(
    request: ClassifyRequest,
    current_user: User = Depends(require_admin),
    _: None = Depends(limit_debug),
) -> dict[str, Any]:
    """Show the production classifier's decision for one query."""
    return await inspect_classification(request.query, str(current_user.id))


@router.post("/rerank")
async def demo_reranking(
    request: RerankRequest,
    _: User = Depends(require_admin),
    __: None = Depends(limit_debug),
) -> dict[str, Any]:
    """Show ordering and scores for supplied candidate snippets."""
    return await inspect_reranking(request.query, request.documents, request.top_k)
