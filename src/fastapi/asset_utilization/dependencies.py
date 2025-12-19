from src.fastapi.asset_utilization.services import UtilizationReportService
from src.fastapi.daily_summary.repositories import (
    DailySummaryRepository,
    IDailySummaryRepository,
)

daily_summary_repo: IDailySummaryRepository = DailySummaryRepository()
utilization_service: UtilizationReportService = UtilizationReportService(
    daily_summary_repo
)


def get_utilization_service() -> UtilizationReportService:
    return utilization_service
