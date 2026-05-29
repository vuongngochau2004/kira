"""Document processing ETL pipeline."""

import sys
import tempfile
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.indexing.file_store import download_file
from src.indexing.qdrant_store import store_chunks
from src.indexing.document_store import update_document_status
from src.ingestion.extractor import extract_content
from src.ingestion.cleaner import clean_document
from src.ingestion.chunker import chunk_document
from src.ingestion.embedding import embed
from src.constants import (
    DOC_STATUS_COMPLETED,
    DOC_STATUS_FAILED,
    ERR_NO_CONTENT,
    ERR_NO_CHUNKS,
    ERR_EXTRACTION_FAILED,
    ERR_PROCESSING_FAILED,
)

DEFAULT_TIMEOUT_SECONDS = 600


async def process_document(
    document_id: UUID,
    user_id: UUID,
    storage_path: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Process document: extract, clean, chunk, embed, store.

    Args:
        document_id: Document ID
        user_id: User ID
        storage_path: MinIO object path
        timeout_seconds: Processing timeout

    Returns:
        Status dict with success/error info
    """
    import asyncio

    try:
        result = await asyncio.to_thread(
            _process_sync,
            document_id,
            user_id,
            storage_path,
        )

        await _update_document_status_result(document_id, result)

        return result

    except Exception as e:
        error_msg = f"{ERR_PROCESSING_FAILED}: {str(e)}"
        import traceback
        print(f"\n[ERROR] Exception in process_document for {document_id}:")
        traceback.print_exc()
        from src.database.session import async_session_factory
        async with async_session_factory() as session:
            await update_document_status(
                document_id=document_id,
                status=DOC_STATUS_FAILED,
                error_message=error_msg,
                db=session,
            )
        return {"success": False, "error": error_msg}


def _process_sync(
    document_id: UUID,
    user_id: UUID,
    storage_path: str,
) -> dict:
    """Synchronous document processing."""
    import asyncio

    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp")
        temp_file.close() # Close immediately to free the file handle lock on Windows

        download_file(storage_path, temp_file.name)
        file_type = storage_path.rsplit(".", 1)[-1] if "." in storage_path else "txt"

        extraction_result = extract_content(temp_file.name, file_type)
        if not extraction_result.success:
            return {"success": False, "error": extraction_result.error or ERR_EXTRACTION_FAILED}

        cleaned_text = clean_document(extraction_result.text)
        if not cleaned_text.strip():
            return {"success": False, "error": ERR_NO_CONTENT}

        chunks = chunk_document(text=cleaned_text, document_id=str(document_id))
        if not chunks:
            return {"success": False, "error": ERR_NO_CHUNKS}

        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = embed(chunk_texts)

        chunk_data = _prepare_chunk_data(chunks)
        qdrant_ids = store_chunks(
            chunks=chunk_data,
            embeddings=embeddings,
            document_id=document_id,
            user_id=user_id,
        )

        _update_chunk_metadata(chunk_data, qdrant_ids)

        return {
            "success": True,
            "chunk_count": len(chunks),
            "chunks": chunk_data,
        }

    finally:
        if temp_file and Path(temp_file.name).exists():
            Path(temp_file.name).unlink()


def _prepare_chunk_data(chunks: list) -> list[dict]:
    """Prepare chunk data for storage."""
    return [
        {
            "index": chunk.index,
            "content": chunk.content,
            "token_count": chunk.token_count,
            "metadata": chunk.metadata,
        }
        for chunk in chunks
    ]


def _update_chunk_metadata(chunk_data: list[dict], qdrant_ids: list) -> None:
    """Update chunk data with Qdrant IDs."""
    for i, chunk_dict in enumerate(chunk_data):
        chunk_dict["metadata"]["qdrant_point_id"] = qdrant_ids[i]


async def _update_document_status_result(document_id: UUID, result: dict) -> None:
    """Update document status based on processing result."""
    from src.database.session import async_session_factory
    async with async_session_factory() as session:
        if result["success"]:
            # Save chunks to PostgreSQL document_chunks table
            from src.indexing.document_store import create_chunks
            await create_chunks(
                document_id=document_id,
                chunks=result["chunks"],
                db=session,
            )

            await update_document_status(
                document_id=document_id,
                status=DOC_STATUS_COMPLETED,
                chunk_count=result["chunk_count"],
                db=session,
            )
        else:
            print(f"\n[ERROR] Document processing failed for {document_id}: {result.get('error')}")
            await update_document_status(
                document_id=document_id,
                status=DOC_STATUS_FAILED,
                error_message=result["error"],
                db=session,
            )


__all__ = ["process_document"]
