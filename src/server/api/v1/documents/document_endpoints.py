"""Document API endpoints - CRUD and processing."""

import asyncio
import io
import mimetypes
import uuid
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.auth.dependencies import get_current_user
from src.constants import (
    DEFAULT_LIMIT,
    DEFAULT_OFFSET,
    DOC_STATUS_COMPLETED,
    DOC_STATUS_FAILED,
    DOC_STATUS_PROCESSING,
    ERR_DOC_NOT_FOUND,
)
from src.shared.infrastructure.persistence.database.session import get_session, async_session_factory
from src.shared.infrastructure.persistence.database.models import User
from src.modules.retrieval.infrastructure.vector import qdrant_store
from src.modules.retrieval.infrastructure.document_store.document_repository import (
    create_document,
    delete_document,
    get_document,
    get_document_chunks,
    list_documents,
    update_document_status,
)
from src.modules.document.infrastructure.storage.storage import download_bytes, upload_bytes
from src.modules.retrieval.infrastructure.keyword.bm25_manager import get_bm25_manager
from src.modules.document.domain.services.pipeline import process_document

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

    await asyncio.to_thread(
        qdrant_store.delete_document,
        uuid.UUID(document_id),
    )


def _resolve_auth_token(
    token_param: str | None,
    request: Request,
) -> str | None:
    """Resolve authentication token from multiple sources.

    Priority order:
    1. Query parameter (token)
    2. Cookie (access_token)
    3. Authorization header (Bearer token)

    Args:
        token_param: Token from query parameter
        request: FastAPI Request object

    Returns:
        Token string or None if not found
    """
    # 1. Check query parameter (explicit token param)
    if token_param:
        return token_param

    # 2. Check cookie (primary strategy for frontend)
    auth_token = request.cookies.get("access_token")
    if auth_token:
        return auth_token

    # 3. Check Authorization header (fallback)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]

    return None


async def _authenticate_and_get_user(
    auth_token: str,
    db: AsyncSession,
) -> User:
    """Validate JWT token and fetch user from database.

    Args:
        auth_token: JWT token string
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    from sqlalchemy import select

    from src.shared.infrastructure.auth.security import decode_token
    from src.shared.infrastructure.persistence.database.models import User

    try:
        payload = decode_token(auth_token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        result = await db.execute(
            select(User).where(User.id == user_id).where(User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        ) from e

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


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
    request: Request,
    token: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    """Stream the raw file from MinIO with inline disposition header.

    Supports multiple authentication methods:
    - Query parameter: ?token=xxx
    - Cookie: access_token=xxx
    - Authorization header: Bearer xxx
    """
    # Step 1: Resolve authentication token from multiple sources
    auth_token = _resolve_auth_token(token, request)

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Step 2: Validate token and get user
    user = await _authenticate_and_get_user(auth_token, db)

    # Step 3: Fetch document metadata
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

    # Step 4: Fetch file bytes from MinIO
    try:
        file_bytes = await asyncio.to_thread(download_bytes, doc.storage_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve file from storage: {e}",
        ) from e

    # Step 5: Guess correct MIME type
    mime_type, _ = mimetypes.guess_type(doc.filename)
    if not mime_type:
        mime_type = "application/octet-stream"

    # Step 6: Build streaming inline response
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=mime_type,
        headers={
            "Content-Disposition": f"inline; filename={doc.filename}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/{document_id}/chunks")
async def get_document_chunks_endpoint(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get all chunks of a document, verifying that the user owns the document."""
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

    chunks = await get_document_chunks(
        document_id=uuid.UUID(document_id),
        db=db,
    )

    return [
        {
            "id": str(chunk.id),
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "metadata": chunk.meta_data,
        }
        for chunk in chunks
    ]
