"""Admin dashboard overview use case."""

from datetime import datetime
from typing import Any, Protocol


class AdminDashboardPort(Protocol):
    async def overview(self, now: datetime) -> dict[str, Any]: ...


class AdminOverview:
    """Return the operational dashboard through a read-model port."""

    def __init__(self, dashboard: AdminDashboardPort):
        self._dashboard = dashboard

    async def execute(self, now: datetime | None = None) -> dict[str, Any]:
        return await self._dashboard.overview(now or datetime.utcnow())


__all__ = ["AdminOverview", "AdminDashboardPort"]
