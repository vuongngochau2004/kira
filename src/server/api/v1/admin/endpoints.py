"""Admin HTTP endpoints."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.admin.composition import admin_overview
from src.shared.infrastructure.auth.dependencies import require_admin
from src.shared.infrastructure.persistence.database.models import User
from src.shared.infrastructure.persistence.database.session import get_session

router = APIRouter()


@router.get("/overview")
async def get_admin_overview(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Return the admin read model; authorization stays at the HTTP edge."""
    overview = await admin_overview(db).execute()
    overview["admin"] = {"id": str(current_user.id), "email": current_user.email}
    return overview


__all__ = ["router"]
