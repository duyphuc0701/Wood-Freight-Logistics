from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.fastapi.daily_summary.schemas import DailyVehicleSummary


class IDailyFuelConsumptionRepository(ABC):
    @abstractmethod
    async def find_by_date_range_and_assets(
        self,
        db_session: AsyncSession,
        start_date: date,
        end_date: date,
        asset_ids: Optional[List[str]],
        page: int,
        page_size: int,
    ) -> List[DailyVehicleSummary]: ...

    @abstractmethod
    async def count_by_date_range_and_assets(
        self,
        db_session: AsyncSession,
        start_date: date,
        end_date: date,
        asset_ids: Optional[List[str]],
    ) -> int: ...
