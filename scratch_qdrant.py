import asyncio
from qdrant_client import AsyncQdrantClient
from src.config.config import settings

async def test():
    client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    res = await client.scroll(
        collection_name=settings.qdrant_collection_name,
        limit=5,
        with_payload=True,
        with_vectors=False
    )
    for point in res[0]:
        print(point.id, point.payload)

asyncio.run(test())
