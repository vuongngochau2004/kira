"""Document processing ETL pipeline."""

import sys
import tempfile
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.indexing.file_store import download_file
from src.indexing.qdrant_store import store_chunks
from src.indexing.document_store import update_document_status
from src.ingestion.extractor import extract_content_sync
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

    print(f"\n[ETL] >>> Starting background pipeline for Document ID: {document_id}")
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
        print(f"\n[ETL ERROR] Exception in process_document for {document_id}:")
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

        print(f"[ETL] [Step 1/7] Downloading file from MinIO: {storage_path}...")
        download_file(storage_path, temp_file.name)
        file_type = storage_path.rsplit(".", 1)[-1] if "." in storage_path else "txt"
        print(f"[ETL] Download complete. File saved to temp path.")

        print(f"[ETL] [Step 2/7] Extracting content (format: {file_type})...")
        extraction_result = extract_content_sync(temp_file.name, file_type)
        if not extraction_result.success:
            print(f"[ETL ERROR] Extraction failed: {extraction_result.error}")
            return {"success": False, "error": extraction_result.error or ERR_EXTRACTION_FAILED}
        
        ext_method = extraction_result.metadata.get("extraction_method", "normal")
        print(f"[ETL] Extraction complete. Method: {ext_method.upper()}, Raw length: {len(extraction_result.text)} characters.")

        # Export OCR text for inspection if OCR was used
        if extraction_result.metadata.get("ocr_used", False):
            try:
                project_root = Path(__file__).resolve().parents[2]
                output_dir = project_root / "data" / "output"
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / f"{document_id}.txt"
                
                header_info = (
                    f"==================================================\n"
                    f"OCR EXPORT FOR INSPECTION\n"
                    f"Document ID: {document_id}\n"
                    f"Original Storage Path: {storage_path}\n"
                    f"Extractor: {extraction_result.metadata.get('extractor')}\n"
                    f"OCR Pages: {extraction_result.metadata.get('ocr_pages')}\n"
                    f"==================================================\n\n"
                )
                
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(header_info)
                    f.write(extraction_result.text)
                
                print(f"[ETL] OCR output successfully exported for inspection to: {output_file}")
            except Exception as e:
                print(f"[ETL WARNING] Failed to export OCR text: {e}")

        print(f"[ETL] [Step 3/7] Cleaning document text...")
        cleaned_text = clean_document(extraction_result.text)
        if not cleaned_text.strip():
            print(f"[ETL ERROR] Document has no content after cleaning.")
            return {"success": False, "error": ERR_NO_CONTENT}
        print(f"[ETL] Cleaning complete. Cleaned length: {len(cleaned_text)} characters.")

        print(f"[ETL] [Step 4/7] Splitting text into chunks...")
        chunks = chunk_document(text=cleaned_text, document_id=str(document_id))
        if not chunks:
            print(f"[ETL ERROR] No chunks generated.")
            return {"success": False, "error": ERR_NO_CHUNKS}
        print(f"[ETL] Chunking complete. Generated {len(chunks)} chunks.")

        print(f"[ETL] [Step 5/7] Generating embeddings via API model server...")
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = embed(chunk_texts)
        print(f"[ETL] Embedding generation complete. Generated {len(embeddings)} vectors.")

        print(f"[ETL] [Step 6/7] Storing chunk vectors in Qdrant Vector DB...")
        chunk_data = _prepare_chunk_data(chunks)
        qdrant_ids = store_chunks(
            chunks=chunk_data,
            embeddings=embeddings,
            document_id=document_id,
            user_id=user_id,
        )
        _update_chunk_metadata(chunk_data, qdrant_ids)
        print(f"[ETL] Storing in Qdrant Vector DB complete.")

        return {
            "success": True,
            "chunk_count": len(chunks),
            "chunks": chunk_data,
        }

    finally:
        if temp_file and Path(temp_file.name).exists():
            try:
                Path(temp_file.name).unlink()
            except Exception as e:
                print(f"[ETL WARNING] Failed to delete temp file {temp_file.name}: {e}")


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
    
    print(f"[ETL] [Step 7/7] Saving chunks and updating final document status in PostgreSQL...")
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
            print(f"[ETL] >>> SUCCESS: Document {document_id} fully processed and indexed successfully!")
        else:
            print(f"\n[ETL ERROR] Document processing failed for {document_id}: {result.get('error')}")
            await update_document_status(
                document_id=document_id,
                status=DOC_STATUS_FAILED,
                error_message=result["error"],
                db=session,
            )


__all__ = ["process_document"]
