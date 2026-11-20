"""Admin dashboard overview use case."""

from datetime import datetime
from typing import Any

from kira.admin.repository import SqlAlchemyAdminDashboardRepository


class AdminOverview:
    """Return the operational dashboard through a read-model port."""

    def __init__(self, dashboard: SqlAlchemyAdminDashboardRepository):
        self._dashboard = dashboard

    async def execute(self, now: datetime | None = None) -> dict[str, Any]:
        return await self._dashboard.overview(now or datetime.utcnow())


__all__ = [
    "AdminOverview",
]
