from datetime import date
from typing import List, Optional, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.fastapi.daily_summary.models import DailyVehicleSummaryModel
from src.fastapi.daily_summary.schemas import DailyVehicleSummary
from src.fastapi.fleet_efficiency.repositories.interface import (
    IDailyFuelConsumptionRepository,
)


class DailyFuelConsumptionRepository(IDailyFuelConsumptionRepository):
    async def find_by_date_range_and_assets(
        self,
        db_session: AsyncSession,
        start_date: date,
        end_date: date,
        asset_ids: Optional[List[str]],
        page: int,
        page_size: int,
    ) -> List[DailyVehicleSummary]:
        stmt = select(DailyVehicleSummaryModel).where(
            DailyVehicleSummaryModel.summary_date.between(start_date, end_date)
        )

        if asset_ids:
            stmt = stmt.where(DailyVehicleSummaryModel.vehicle_id.in_(asset_ids))

        # Add pagination logic
        offset = (page - 1) * page_size
        stmt = (
            stmt.order_by(DailyVehicleSummaryModel.summary_date)
            .offset(offset)
            .limit(page_size)
        )

        result = await db_session.execute(stmt)
        records = result.scalars().all()

        return [DailyVehicleSummary.model_validate(r.__dict__) for r in records]

    async def count_by_date_range_and_assets(
        self,
        db_session: AsyncSession,
        start_date: date,
        end_date: date,
        asset_ids: Optional[List[str]],
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(DailyVehicleSummaryModel)
            .where(DailyVehicleSummaryModel.summary_date.between(start_date, end_date))
        )

        if asset_ids:
            stmt = stmt.where(DailyVehicleSummaryModel.vehicle_id.in_(asset_ids))

        result = await db_session.execute(stmt)
        return cast(int, result.scalar_one())
