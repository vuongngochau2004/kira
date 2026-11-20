"""Worker-wide event loop shared by every Celery task module.

asyncpg connection pools are bound to the loop that created them, so all tasks in a
worker process must run on the same loop.
"""

import asyncio

_worker_event_loop: asyncio.AbstractEventLoop | None = None


def get_worker_event_loop() -> asyncio.AbstractEventLoop:
    """Get or create the worker-local event loop."""
    global _worker_event_loop
    if _worker_event_loop is None or _worker_event_loop.is_closed():
        _worker_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_event_loop)
    return _worker_event_loop
