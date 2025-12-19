from abc import ABC, abstractmethod
from datetime import date
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.fastapi.idling_hotspots.schemas import IdlingHotspot


class IIdlingDataRepository(ABC):
    @abstractmethod
    async def fetch_idling_records(
        self,
        db_session: AsyncSession,
        start_date: date,
        end_date: date,
        min_idle_duration_minutes: int,
        page: int,
        page_size: int,
    ) -> Tuple[List[IdlingHotspot], int]: ...
