import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.fastapi.idling_hotspots.repositories.interface import IIdlingDataRepository
from src.fastapi.idling_hotspots.schemas import IdlingHotspotRequestDTO
from src.fastapi.idling_hotspots.strategies.factory import SpatialGrouperFactory

logger = logging.getLogger(__name__)


class IdlingReportService:
    def __init__(self, idling_repo: IIdlingDataRepository):
        self.idling_repo = idling_repo

    async def get_idling_hotspots_report(
        self, db_session: AsyncSession, params: IdlingHotspotRequestDTO
    ):
        try:
            records, total = await self.idling_repo.fetch_idling_records(
                db_session=db_session,
                start_date=params.date_range_start,
                end_date=params.date_range_end,
                min_idle_duration_minutes=params.min_idle_duration_minutes,
                page=params.page,
                page_size=params.page_size,
            )
        except Exception as e:
            logger.error("Failed to fetch idling records", exc_info=e)
            raise RuntimeError(
                "An error occurred while fetching idling records."
            ) from e

        try:
            strategy = SpatialGrouperFactory.create(params.aggregation_level)
            grouped = strategy.group(records, params.aggregation_level)
        except Exception as e:
            logger.error("Failed to group idling records", exc_info=e)
            raise RuntimeError(
                "An error occurred while grouping idling records."
            ) from e

        return grouped, total
