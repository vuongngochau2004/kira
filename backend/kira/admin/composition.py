from sqlalchemy.ext.asyncio import AsyncSession

from kira.admin.repository import SqlAlchemyAdminDashboardRepository
from kira.admin.service import AdminOverview


def admin_overview(db: AsyncSession) -> AdminOverview:
    return AdminOverview(SqlAlchemyAdminDashboardRepository(db))
