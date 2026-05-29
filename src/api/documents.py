"""Document API endpoints - CRUD and processing."""

import sys
import uuid
import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.database import get_session
from src.database.session import async_session_factory
from src.indexing.file_store import upload_bytes
from src.indexing.document_store import (
    create_document,
    get_document,
    list_documents,
    delete_document,
    update_document_status,
)
from src.ingestion.pipelines import process_document
from src.ingestion.bm25_builder import get_bm25_manager
from src.auth.dependencies import get_current_user
from src.database.models import User
from src.constants import (
    DEFAULT_LIMIT,
    DEFAULT_OFFSET,
    DOC_STATUS_UPLOADING,
    DOC_STATUS_PROCESSING,
    DOC_STATUS_COMPLETED,
    DOC_STATUS_FAILED,
    ERR_DOC_NOT_FOUND,
)

router = APIRouter()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Upload a document and start processing."""
    content = await file.read()
    file_ext = _get_file_extension(file.filename)
    storage_path = f"{current_user.id}/{uuid.uuid4()}.{file_ext}"

    await asyncio.to_thread(
        upload_bytes,
        data=content,
        object_name=storage_path,
        content_type=file.content_type,
    )

    doc = await create_document(
        user_id=current_user.id,
        filename=file.filename,
        file_type=file_ext,
        file_size=len(content),
        storage_path=storage_path,
        db=db,
    )

    if background_tasks:
        background_tasks.add_task(
            _process_document_background,
            str(doc.id),
            str(current_user.id),
            storage_path,
        )

    return _serialize_document(doc)


def _get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    return filename.rsplit(".", 1)[-1] if "." in filename else "txt"


async def _process_document_background(
    document_id: str,
    user_id: str,
    storage_path: str,
):
    """Background task for document processing."""
    try:
        async with async_session_factory() as session:
            await update_document_status(
                document_id=uuid.UUID(document_id),
                status=DOC_STATUS_PROCESSING,
                db=session,
            )

        result = await process_document(
            document_id=uuid.UUID(document_id),
            user_id=uuid.UUID(user_id),
            storage_path=storage_path,
        )

        if result["success"]:
            bm25_manager = get_bm25_manager()
            bm25_manager.add_document_bulk(
                user_id=user_id,
                chunks=result.get("chunks", []),
            )

    except Exception as e:
        async with async_session_factory() as session:
            await update_document_status(
                document_id=uuid.UUID(document_id),
                status=DOC_STATUS_FAILED,
                error_message=str(e),
                db=session,
            )


@router.get("")
async def list_user_documents(
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
    status_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List user's documents."""
    documents, total = await list_documents(
        user_id=current_user.id,
        status=status_filter,
        limit=limit,
        offset=offset,
        db=db,
    )

    return {
        "documents": [_serialize_document(doc) for doc in documents],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _serialize_document(doc: Any) -> dict:
    """Serialize document to dict."""
    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
    }


@router.get("/{document_id}")
async def get_document_info(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get document details."""
    doc = await get_document(
        document_id=uuid.UUID(document_id),
        user_id=current_user.id,
        db=db,
    )

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_DOC_NOT_FOUND,
        )

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "error_message": doc.error_message,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
    }


@router.delete("/{document_id}")
async def delete_user_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Delete a document."""
    success = await delete_document(
        document_id=uuid.UUID(document_id),
        user_id=current_user.id,
        db=db,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_DOC_NOT_FOUND,
        )

    await _cleanup_document_resources(current_user.id, document_id)

    return {"message": "Document deleted"}


async def _cleanup_document_resources(user_id: uuid.UUID, document_id: str):
    """Clean up document resources from BM25 and Qdrant."""
    bm25_manager = get_bm25_manager()
    bm25_manager.remove_document(str(user_id), document_id)

    import src.indexing.qdrant_store as vector_store
    await asyncio.to_thread(
        vector_store.delete_document,
        uuid.UUID(document_id),
    )


@router.post("/{document_id}/process")
async def trigger_processing(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Manually trigger document processing."""
    doc = await get_document(
        document_id=uuid.UUID(document_id),
        user_id=current_user.id,
        db=db,
    )

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_DOC_NOT_FOUND,
        )

    if doc.status == DOC_STATUS_COMPLETED:
        return {"message": "Document already processed"}

    background_tasks.add_task(
        _process_document_background,
        str(doc.id),
        str(current_user.id),
        doc.storage_path,
    )

    return {"message": "Processing triggered"}





@router.get("/{document_id}/download")
async def download_document_file(
    document_id: str,
    token: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    """Stream the raw file from MinIO with inline disposition header."""
    import mimetypes
    import io
    from fastapi.responses import StreamingResponse

    # Resolve authenticated user (supports both standard headers and token query parameter)
    from config.config import settings
    user = None
    if not settings.auth_enabled:
        from src.auth.dependencies import _get_or_create_dev_user
        user = await _get_or_create_dev_user(db)
    else:
        # Fallback to token query param if header authentication is absent
        auth_token = token
        if not auth_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        try:
            from src.auth.security import decode_token
            payload = decode_token(auth_token)
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )
            
            from sqlalchemy import select
            from src.database.models import User
            result = await db.execute(
                select(User).where(User.id == user_id).where(User.deleted_at.is_(None))
            )
            user = result.scalar_one_or_none()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {e}",
            )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Fetch document metadata
    doc = await get_document(
        document_id=uuid.UUID(document_id),
        user_id=user.id,
        db=db,
    )

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_DOC_NOT_FOUND,
        )

    # Fetch file bytes from MinIO
    from src.indexing.file_store import download_bytes
    try:
        file_bytes = await asyncio.to_thread(download_bytes, doc.storage_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve file from storage: {e}",
        )

    # Guess correct MIME type
    mime_type, _ = mimetypes.guess_type(doc.filename)
    if not mime_type:
        mime_type = "application/octet-stream"

    # Streaming inline response
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=mime_type,
        headers={
            "Content-Disposition": f"inline; filename={doc.filename}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )

