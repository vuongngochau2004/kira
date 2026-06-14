import asyncio
from uuid import UUID
from src.modules.retrieval.infrastructure.document_store.document_repository import get_documents_batch

async def main():
    doc_ids = ["0b38d84b-e3af-4dba-83a4-4ad6ca3468f4", "91bcae6b-f840-4c25-95d3-78e30cae7250"]
    try:
        mapping = await get_documents_batch(doc_ids)
        print("Mapping:", mapping)
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
