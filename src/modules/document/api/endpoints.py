"""Document API endpoints - CRUD and processing."""

import io
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
    DocumentStatus,
    ERR_DOC_NOT_FOUND,
)
from src.shared.infrastructure.persistence.database.session import async_session_factory, get_session
from src.shared.infrastructure.persistence.database.models import User
from src.modules.document.application import (
    DeleteDocumentRequest,
    DownloadDocument,
    DownloadDocumentRequest,
    GetDocument,
    GetDocumentChunks,
    GetDocumentChunksRequest,
    GetDocumentRequest,
    ListDocuments,
    ListDocumentsRequest,
    ProcessDocumentRequest,
    UploadDocumentRequest,
)
from src.modules.document.composition import (
    delete_document_service,
    document_repository,
    process_document_service,
    storage_adapter,
    upload_document_service,
)

router = APIRouter()


async def _process_document_background(request: ProcessDocumentRequest) -> None:
    """Run document processing with a fresh background DB session."""
    async with async_session_factory() as session:
        await process_document_service(session).execute(request)


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
    upload_result = await upload_document_service(db).execute(
        UploadDocumentRequest(
            file_name=file.filename,
            user_id=current_user.id,
            file_type=file_ext,
            file_content=content,
            file_size=len(content),
            content_type=file.content_type,
        )
    )

    if upload_result.status != "success" or upload_result.document is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=upload_result.message,
        )

    if background_tasks:
        background_tasks.add_task(
            _process_document_background,
            ProcessDocumentRequest(
                document_id=upload_result.document_id,
                user_id=current_user.id,
                storage_path=upload_result.storage_path or "",
            ),
        )

    return _serialize_document(upload_result.document)


def _get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    return filename.rsplit(".", 1)[-1] if "." in filename else "txt"


@router.get("")
async def list_user_documents(
    limit: int = DEFAULT_LIMIT,
    offset: int = DEFAULT_OFFSET,
    status_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List user's documents."""
    result = await ListDocuments(repository=document_repository(db)).execute(
        ListDocumentsRequest(
            user_id=current_user.id,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    )

    return {
        "documents": [_serialize_document(doc) for doc in result.documents],
        "total": result.total,
        "limit": result.limit,
        "offset": result.offset,
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
    result = await GetDocument(repository=document_repository(db)).execute(
        GetDocumentRequest(
            document_id=uuid.UUID(document_id),
            user_id=current_user.id,
        )
    )

    doc = result.document
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
    result = await delete_document_service(db).execute(
        DeleteDocumentRequest(
            document_id=uuid.UUID(document_id),
            user_id=current_user.id,
        )
    )

    if not result.success:
        if result.message == "Document not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERR_DOC_NOT_FOUND,
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.message,
        )

    return {"message": "Document deleted"}


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
    result = await GetDocument(repository=document_repository(db)).execute(
        GetDocumentRequest(
            document_id=uuid.UUID(document_id),
            user_id=current_user.id,
        )
    )

    doc = result.document
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_DOC_NOT_FOUND,
        )

    if doc.status == DocumentStatus.COMPLETED.value:
        return {"message": "Document already processed"}

    background_tasks.add_task(
        _process_document_background,
        ProcessDocumentRequest(
            document_id=doc.id,
            user_id=current_user.id,
            storage_path=doc.storage_path,
        ),
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

    download_result = await DownloadDocument(
        repository=document_repository(db),
        storage=storage_adapter(),
    ).execute(
        DownloadDocumentRequest(
            document_id=uuid.UUID(document_id),
            user_id=user.id,
        )
    )

    if not download_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_DOC_NOT_FOUND,
        )

    return StreamingResponse(
        io.BytesIO(download_result.file_bytes),
        media_type=download_result.media_type,
        headers={
            "Content-Disposition": f"inline; filename={download_result.filename}",
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
    result = await GetDocumentChunks(repository=document_repository(db)).execute(
        GetDocumentChunksRequest(
            document_id=uuid.UUID(document_id),
            user_id=current_user.id,
        )
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_DOC_NOT_FOUND,
        )

    return [
        {
            "id": str(chunk.id),
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "metadata": chunk.meta_data,
        }
        for chunk in result.chunks
    ]
