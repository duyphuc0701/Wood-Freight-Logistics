from datetime import date
from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.fastapi.idling_hotspots.models import IdlingHotspotModel
from src.fastapi.idling_hotspots.repositories.interface import IIdlingDataRepository
from src.fastapi.idling_hotspots.schemas import IdlingDetectedEvent, IdlingHotspot


class IdlingDataRepository(IIdlingDataRepository):
    async def save_idling_event(
        self,
        db_session: AsyncSession,
        idling_event: IdlingDetectedEvent,
    ) -> None:
        model = IdlingHotspotModel(
            asset_id=idling_event.device_id,
            date=idling_event.start_time.date(),
            idle_duration_minutes=(
                (idling_event.end_time - idling_event.start_time).total_seconds() / 60.0
            ),
            latitude=idling_event.latitude,
            longitude=idling_event.longitude,
        )
        db_session.add(model)
        await db_session.commit()

    async def fetch_idling_records(
        self,
        db_session: AsyncSession,
        start_date: date,
        end_date: date,
        min_idle_duration_minutes: int,
        page: int,
        page_size: int,
    ) -> Tuple[List[IdlingHotspot], int]:
        stmt = (
            select(IdlingHotspotModel)
            .where(
                IdlingHotspotModel.date >= start_date,
                IdlingHotspotModel.date <= end_date,
                IdlingHotspotModel.idle_duration_minutes >= min_idle_duration_minutes,
            )
            .limit(page_size)
            .offset((page - 1) * page_size)
        )

        count_stmt = (
            select(func.count())
            .select_from(IdlingHotspotModel)
            .where(
                IdlingHotspotModel.date >= start_date,
                IdlingHotspotModel.date <= end_date,
                IdlingHotspotModel.idle_duration_minutes >= min_idle_duration_minutes,
            )
        )

        result = await db_session.execute(stmt)
        count_result = await db_session.execute(count_stmt)

        records = result.scalars().all()
        total_count = count_result.scalar_one()

        return (
            [IdlingHotspot.model_validate(r.__dict__) for r in records],
            total_count,
        )
