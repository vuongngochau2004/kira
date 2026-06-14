import asyncio
from src.modules.retrieval.infrastructure.vector_store.qdrant_store import QdrantVectorStore

async def main():
    store = QdrantVectorStore()
    results = await store.search([0.0]*1024, k=1)
    for r in results:
        print("Point metadata:", r.metadata)

asyncio.run(main())
