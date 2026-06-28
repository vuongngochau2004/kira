#!/usr/bin/env python3
"""Script to clean up and delete all uploaded documents from DB, Qdrant, MinIO, and BM25 index."""

import sys
import asyncio
from pathlib import Path
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.shared.infrastructure.persistence.database.session import async_session_factory
from src.shared.infrastructure.persistence.database.models import Document
from src.modules.document.composition import delete_document_service
from src.modules.document.application.dto import DeleteDocumentRequest

async def clean_all_documents():
    print("Connecting to database...")
    async with async_session_factory() as db:
        # Fetch all documents in the database
        result = await db.execute(select(Document).where(Document.deleted_at.is_(None)))
        documents = result.scalars().all()
        
        if not documents:
            print("No documents found in the database.")
            return

        print(f"Found {len(documents)} documents to delete.")
        
        service = delete_document_service(db)
        
        for idx, doc in enumerate(documents, 1):
            print(f"[{idx}/{len(documents)}] Deleting document: {doc.filename} (ID: {doc.id}) for user: {doc.user_id}...")
            try:
                # Run the DeleteDocument use case which cleans up Qdrant, MinIO, and BM25
                req = DeleteDocumentRequest(document_id=doc.id, user_id=doc.user_id)
                res = await service.execute(req)
                if res.success:
                    print(f"   Success: {res.message}")
                else:
                    print(f"   Failed: {res.message}")
            except Exception as e:
                print(f"   Error: {e}")

        # Also empty DocumentChunk table just in case there are orphaned chunks
        # Actually soft-deletion or cascade should handle it, but we can verify.
        await db.commit()
    print("Database cleanup process finished.")

def main():
    try:
        asyncio.run(clean_all_documents())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
