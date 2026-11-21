"""Admin HTTP endpoints."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from kira.auth.dependencies import require_admin
from kira.core.health import get_system_overview
from kira.db.models import User
from kira.db.session import get_session
from kira.deps import admin_overview
from kira.retrieval.rerank.service import get_llm_client

router = APIRouter()


@router.get("/overview")
async def get_admin_overview(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Return the admin read model; authorization stays at the HTTP edge."""
    overview = await admin_overview(db).execute()
    overview["admin"] = {"id": str(current_user.id), "email": current_user.email}
    try:
        overview["system"] = await get_system_overview(get_llm_client())
    except Exception:
        overview["system"] = {"status": "ok", "services": []}
    return overview


__all__ = ["router"]
