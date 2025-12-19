import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.fastapi.asset_utilization.schemas import AssetUtilizationRequestDTO
from src.fastapi.asset_utilization.strategies.factory import UtilizationStrategyFactory
from src.fastapi.daily_summary.repositories import IDailySummaryRepository

logger = logging.getLogger(__name__)


class UtilizationReportService:
    def __init__(self, repository: IDailySummaryRepository):
        self.repository = repository

    async def generate_report(
        self, db_session: AsyncSession, params: AssetUtilizationRequestDTO
    ):
        try:
            # Fetch paginated and sorted summaries
            summaries, total = await self.repository.fetch_with_date_range(
                db_session=db_session,
                date_start=params.date_range_start,
                date_end=params.date_range_end,
                page=params.page,
                page_size=params.page_size,
                sort_by=params.sort_by,
                sort_order=params.sort_order,
                report_by=params.report_by,
            )

            # Select strategy
            strategy = UtilizationStrategyFactory.create(
                report_by=params.report_by,
                target_km_per_day=params.target_km_per_day,
                target_hours_per_day=params.target_hours_per_day,
            )

            # Compute utilization per asset-day
            results = [strategy.calculate(summary) for summary in summaries]

            return results, total

        except ValueError as e:
            logger.warning("Validation error: %s", str(e), exc_info=True)
            raise

        except SQLAlchemyError as e:
            logger.error("Database error: %s", str(e), exc_info=True)
            raise RuntimeError(
                "Failed to generate report due to a database error."
            ) from e

        except Exception as e:
            logger.error("Unexpected error: %s", str(e), exc_info=True)
            raise RuntimeError(
                "Unexpected error while generating asset utilization report."
            ) from e
