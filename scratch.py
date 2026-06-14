import asyncio
from uuid import UUID
from sqlalchemy import select
from src.shared.infrastructure.persistence.database.models import Document
from src.shared.infrastructure.persistence.database.session import async_session_factory

async def test():
    async with async_session_factory() as session:
        result = await session.execute(select(Document))
        docs = result.scalars().all()
        for d in docs:
            print(d.id, d.filename, d.status)

asyncio.run(test())
