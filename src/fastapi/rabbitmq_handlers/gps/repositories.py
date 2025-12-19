from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.fastapi.rabbitmq_handlers.gps.models import GPSEventModel
from src.fastapi.rabbitmq_handlers.gps.schemas import GPSEventResponse


class IGpsEventRepository(ABC):
    @abstractmethod
    async def exists(self, db: AsyncSession, device_id: str) -> bool:
        pass

    @abstractmethod
    async def fetch_by_day(
        self, db: AsyncSession, device_id: str, day: date
    ) -> List[GPSEventModel]:
        pass

    @abstractmethod
    async def save(self, db: AsyncSession, event: GPSEventResponse) -> None:
        pass


class GpsEventRepository(IGpsEventRepository):
    async def exists(self, db: AsyncSession, device_id: str) -> bool:
        q = await db.execute(
            select(GPSEventModel.id)
            .where(GPSEventModel.device_id == device_id)
            .limit(1)
        )
        return q.scalars().first() is not None

    async def fetch_by_day(
        self, db: AsyncSession, device_id: str, day: date
    ) -> List[GPSEventModel]:
        start = datetime.combine(day, datetime.min.time())
        end = start + timedelta(days=1)
        q = await db.execute(
            select(GPSEventModel).where(
                GPSEventModel.device_id == device_id,
                GPSEventModel.timestamp >= start,
                GPSEventModel.timestamp < end,
            )
        )
        return list(q.scalars().all())

    async def save(self, db: AsyncSession, event: GPSEventResponse) -> None:
        model = GPSEventModel(**event.model_dump())
        db.add(model)
        await db.commit()
        await db.refresh(model)
