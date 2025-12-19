import logging
from typing import List, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.fastapi.fleet_efficiency.repositories.interface import (
    IDailyFuelConsumptionRepository,
)
from src.fastapi.fleet_efficiency.schemas import (
    FleetEfficiencyRequestDTO,
    FleetEfficiencyResponseDTO,
)
from src.fastapi.fleet_efficiency.strategies.factory import (
    FleetEfficiencyStrategyFactory,
)

logger = logging.getLogger(__name__)


class FleetEfficiencyService:
    def __init__(self, fuel_consumption_repo: IDailyFuelConsumptionRepository):
        self.fuel_consumption_repo = fuel_consumption_repo

    async def get_efficiency_report(
        self,
        db_session: AsyncSession,
        params: FleetEfficiencyRequestDTO,
        asset_ids: List[str] | None,
    ) -> Tuple[FleetEfficiencyResponseDTO, int]:
        try:
            if asset_ids:
                logger.info("List of asset ids", ", ".join(asset_ids))
            else:
                logger.info("No asset ids")
            # Fetch data from database through repository
            summaries = await self.fuel_consumption_repo.find_by_date_range_and_assets(
                db_session=db_session,
                start_date=params.date_range_start,
                end_date=params.date_range_end,
                asset_ids=asset_ids,
                page=params.page,
                page_size=params.page_size,
            )

            total = await self.fuel_consumption_repo.count_by_date_range_and_assets(
                db_session=db_session,
                start_date=params.date_range_start,
                end_date=params.date_range_end,
                asset_ids=asset_ids,
            )

            # Aggregate data based on requested strategy
            strategy = FleetEfficiencyStrategyFactory.create(
                granularity=params.granularity
            )

            records = await strategy.aggregate(summaries=summaries, asset_ids=asset_ids)

            return records, total

        except ValueError as e:
            logger.warning(
                "Validation error in fleet efficiency report: %s", str(e), exc_info=True
            )
            raise

        except SQLAlchemyError as e:
            logger.error(
                "Database error while generating fleet efficiency report: %s",
                str(e),
                exc_info=True,
            )
            raise RuntimeError(
                "Database error during fleet efficiency report generation."
            ) from e

        except Exception as e:
            logger.error(
                "Unexpected error during fleet efficiency report generation: %s",
                str(e),
                exc_info=True,
            )
            raise RuntimeError(
                "Unexpected error during fleet efficiency report generation."
            ) from e
