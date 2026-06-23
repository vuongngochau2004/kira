from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.admin.application.overview import AdminOverview
from src.modules.admin.infrastructure.dashboard_repository import SqlAlchemyAdminDashboardRepository
def admin_overview(db: AsyncSession) -> AdminOverview: return AdminOverview(SqlAlchemyAdminDashboardRepository(db))
