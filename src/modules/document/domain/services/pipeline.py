"""Document processing ETL pipeline.

Migrated from src/ingestion/pipelines.py
"""

import asyncio
import logging
import tempfile
import uuid
from pathlib import Path
from uuid import UUID
from src.modules.document.domain.models import Chunk
from src.modules.document.domain.services.extractor import extract_content_sync
from src.modules.document.domain.services.cleaner import clean_document
from src.modules.document.domain.services.chunker import chunk_document
from src.constants import (
    DocumentStatus,
    ERR_NO_CONTENT,
    ERR_NO_CHUNKS,
    ERR_EXTRACTION_FAILED,
    ERR_PROCESSING_FAILED,
)
from src.shared.ports.document_repository import DocumentRepositoryPort
from src.shared.ports.embedding import EmbeddingPort
from src.shared.ports.ocr import OCRPort
from src.shared.ports.storage import StoragePort
from src.shared.ports.vector_store import VectorDocument, VectorStorePort

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 600


async def process_document(
    document_id: UUID,
    user_id: UUID,
    storage_path: str,
    storage: StoragePort,
    embedding: EmbeddingPort,
    vector_store: VectorStorePort,
    ocr: OCRPort,
    repository: DocumentRepositoryPort,
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
    logger.info(">>> Starting background pipeline for Document ID: %s", document_id)
    try:
        result = await asyncio.to_thread(
            _process_sync,
            document_id,
            user_id,
            storage_path,
            await storage.download(storage_path),
            embedding,
            vector_store,
            ocr,
        )

        document = await repository.get_document(document_id=document_id, user_id=user_id)
        if not document or document.status == DocumentStatus.CANCELLED.value:
            logger.info("Document %s was cancelled before final persistence; cleaning vectors.", document_id)
            try:
                await vector_store.delete_document(document_id)
            except Exception:
                logger.warning(
                    "Failed to clean vector entries for cancelled document %s",
                    document_id,
                    exc_info=True,
                )
            return {"success": False, "error": "Document processing cancelled", "cancelled": True}

        await _update_document_status_result(document_id, result, repository)

        return result

    except Exception as e:
        error_msg = f"{ERR_PROCESSING_FAILED}: {str(e)}"
        logger.error("Exception in process_document for %s: %s", document_id, e, exc_info=True)
        await repository.update_document_status(
            document_id=document_id,
            status=DocumentStatus.FAILED.value,
            error_message=error_msg,
        )
        return {"success": False, "error": error_msg}


def _process_sync(
    document_id: UUID,
    user_id: UUID,
    storage_path: str,
    file_bytes: bytes,
    embedding: EmbeddingPort,
    vector_store: VectorStorePort,
    ocr: OCRPort,
) -> dict:
    """Synchronous document processing."""
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp")
        temp_file.close()  # Close immediately to free the file handle lock on Windows

        logger.info("[Step 1/7] Writing downloaded file to temp path: %s", storage_path)
        Path(temp_file.name).write_bytes(file_bytes)
        file_type = storage_path.rsplit(".", 1)[-1] if "." in storage_path else "txt"
        logger.info("File saved to temp path.")

        logger.info("[Step 2/7] Extracting content (format: %s)...", file_type)
        extraction_result = extract_content_sync(temp_file.name, file_type, ocr=ocr)
        if not extraction_result.success:
            logger.error("Extraction failed: %s", extraction_result.error)
            return {"success": False, "error": extraction_result.error or ERR_EXTRACTION_FAILED}

        ext_method = extraction_result.metadata.get("extraction_method", "normal")
        logger.info(
            "Extraction complete. Method: %s, Raw length: %d characters.",
            ext_method.upper(),
            len(extraction_result.text)
        )

        # Export OCR text for inspection if OCR was used
        if extraction_result.metadata.get("ocr_used", False):
            try:
                project_root = Path(__file__).resolve().parents[4]  # Adjusted for new module path
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

                logger.info("OCR output successfully exported for inspection to: %s", output_file)
            except Exception as e:
                logger.warning("Failed to export OCR text: %s", e)

        logger.info("[Step 3/7] Cleaning document text...")
        cleaned_text = clean_document(extraction_result.text)
        if not cleaned_text.strip():
            logger.error("Document has no content after cleaning.")
            return {"success": False, "error": ERR_NO_CONTENT}
        logger.info("Cleaning complete. Cleaned length: %d characters.", len(cleaned_text))

        logger.info("[Step 4/7] Splitting text into chunks...")
        chunks = chunk_document(text=cleaned_text, document_id=str(document_id))
        if not chunks:
            logger.error("No chunks generated.")
            return {"success": False, "error": ERR_NO_CHUNKS}
        logger.info("Chunking complete. Generated %d chunks.", len(chunks))

        logger.info("[Step 5/7] Generating embeddings via API model server...")
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = asyncio.run(embedding.embed_batch(chunk_texts))
        logger.info("Embedding generation complete. Generated %d vectors.", len(embeddings))

        logger.info("[Step 6/7] Storing chunk vectors in vector store...")
        chunk_data = _prepare_chunk_data(chunks)
        vector_documents, qdrant_ids = _prepare_vector_documents(
            chunk_data=chunk_data,
            embeddings=embeddings,
            document_id=document_id,
            user_id=user_id,
        )
        asyncio.run(vector_store.upsert(vector_documents))
        _update_chunk_metadata(chunk_data, qdrant_ids)
        logger.info("Storing in vector store complete.")

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
                logger.warning("Failed to delete temp file %s: %s", temp_file.name, e)


def _prepare_chunk_data(chunks: list[Chunk]) -> list[dict]:
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


def _prepare_vector_documents(
    chunk_data: list[dict],
    embeddings: list[list[float]],
    document_id: UUID,
    user_id: UUID,
) -> tuple[list[VectorDocument], list[str]]:
    """Prepare vector documents and stable vector IDs."""
    vector_documents = []
    qdrant_ids = []

    for i, (chunk, chunk_embedding) in enumerate(zip(chunk_data, embeddings)):
        chunk_index = chunk.get("index", i)
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}_chunk_{chunk_index}"))
        qdrant_ids.append(point_id)
        vector_documents.append(
            VectorDocument(
                id=point_id,
                text=chunk.get("content", ""),
                embedding=chunk_embedding,
                metadata={
                    "document_id": str(document_id),
                    "user_id": str(user_id),
                    "chunk_index": chunk_index,
                    **chunk.get("metadata", {}),
                },
            )
        )

    return vector_documents, qdrant_ids


async def _update_document_status_result(
    document_id: UUID,
    result: dict,
    repository: DocumentRepositoryPort,
) -> None:
    """Update document status based on processing result."""
    logger.info("[Step 7/7] Saving chunks and updating final document status in PostgreSQL...")
    if result["success"]:
        await repository.create_chunks(
            document_id=document_id,
            chunks=result["chunks"],
        )

        await repository.update_document_status(
            document_id=document_id,
            status=DocumentStatus.COMPLETED.value,
            chunk_count=result["chunk_count"],
        )
        logger.info(">>> SUCCESS: Document %s fully processed and indexed successfully!", document_id)
    else:
        logger.error("Document processing failed for %s: %s", document_id, result.get('error'))
        await repository.update_document_status(
            document_id=document_id,
            status=DocumentStatus.FAILED.value,
            error_message=result["error"],
        )


__all__ = ["process_document"]
