from abc import ABC, abstractmethod
from datetime import date
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession

from src.fastapi.gps_devices.exceptions import (
    GPSDeviceNotFoundException,
    GPSNotFoundException,
)
from src.fastapi.rabbitmq_handlers.gps.repositories import IGpsEventRepository


class IGpsStatsService(ABC):
    @abstractmethod
    async def calculate_stats(
        self, db: AsyncSession, device_id: str, day: date
    ) -> Dict:
        pass


class GpsStatsService(IGpsStatsService):
    def __init__(self, gps_repo: IGpsEventRepository):
        self._repo = gps_repo

    async def calculate_stats(
        self, db: AsyncSession, device_id: str, day: date
    ) -> Dict:
        # 1. check existence
        if not await self._repo.exists(db, device_id):
            raise GPSDeviceNotFoundException(device_id)

        # 2. fetch events
        events = await self._repo.fetch_by_day(db, device_id, day)
        if not events:
            raise GPSNotFoundException(device_id, day.isoformat())

        # 3. compute metrics
        events.sort(key=lambda e: e.timestamp)
        distance = (events[-1].odometer - events[0].odometer) if len(events) > 1 else 0
        avg_speed = sum(e.speed for e in events) / len(events)
        miles = distance * 0.621371

        return {
            "device_id": device_id,
            "date": day.isoformat(),
            "total_distance_km": distance,
            "total_distance_miles": miles,
            "average_speed": avg_speed,
        }
