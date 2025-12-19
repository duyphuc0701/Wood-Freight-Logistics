import logging
from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional, Tuple, cast

from sqlalchemy import asc, desc, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.fastapi.daily_summary.models import DailyVehicleSummaryModel
from src.fastapi.daily_summary.schemas import DailyVehicleSummary

logger = logging.getLogger(__name__)


class IDailySummaryRepository(ABC):
    @abstractmethod
    async def get_summary(
        self, db: AsyncSession, vehicle_id: str, summary_date: date
    ) -> Optional[DailyVehicleSummaryModel]:
        pass

    @abstractmethod
    async def increment_trip_count(self, db: AsyncSession, vehicle_id: str, date: date):
        pass

    @abstractmethod
    async def increment_distance(
        self, db: AsyncSession, vehicle_id: str, date: date, distance: float
    ):
        pass

    @abstractmethod
    async def increment_operational_seconds(
        self, db: AsyncSession, vehicle_id: str, date: date, seconds: float
    ):
        pass

    @abstractmethod
    async def upsert_summary(self, db: AsyncSession, summary: DailyVehicleSummaryModel):
        pass

    @abstractmethod
    async def fetch_with_date_range(
        self,
        db_session: AsyncSession,
        date_start: date,
        date_end: date,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        report_by: str,
    ) -> Tuple[List[DailyVehicleSummary], int]:
        """Returns (summaries, total_count)"""
        ...


class DailySummaryRepository(IDailySummaryRepository):
    async def get_summary(
        self, db: AsyncSession, vehicle_id: str, summary_date: date
    ) -> Optional[DailyVehicleSummaryModel]:
        q = await db.execute(
            select(DailyVehicleSummaryModel).where(
                DailyVehicleSummaryModel.vehicle_id == vehicle_id,
                DailyVehicleSummaryModel.summary_date == summary_date,
            )
        )
        return cast(DailyVehicleSummaryModel, q.scalar_one_or_none())

    async def increment_trip_count(self, db: AsyncSession, vehicle_id: str, date: date):
        await db.execute(
            update(DailyVehicleSummaryModel)
            .where(
                DailyVehicleSummaryModel.vehicle_id == vehicle_id,
                DailyVehicleSummaryModel.summary_date == date,
            )
            .values(trip_count=DailyVehicleSummaryModel.trip_count + 1)
        )
        await db.commit()

    async def increment_distance(
        self, db: AsyncSession, vehicle_id: str, date: date, distance: float
    ):
        await db.execute(
            update(DailyVehicleSummaryModel)
            .where(
                DailyVehicleSummaryModel.vehicle_id == vehicle_id,
                DailyVehicleSummaryModel.summary_date == date,
            )
            .values(
                total_distance_km=DailyVehicleSummaryModel.total_distance_km + distance
            )
        )
        await db.commit()

    async def increment_operational_seconds(
        self, db: AsyncSession, vehicle_id: str, date: date, seconds: float
    ):
        await db.execute(
            update(DailyVehicleSummaryModel)
            .where(
                DailyVehicleSummaryModel.vehicle_id == vehicle_id,
                DailyVehicleSummaryModel.summary_date == date,
            )
            .values(
                total_operational_hours=DailyVehicleSummaryModel.total_operational_hours
                + seconds
            )
        )
        await db.commit()

    async def upsert_summary(self, db: AsyncSession, summary: DailyVehicleSummaryModel):
        stmt = (
            insert(DailyVehicleSummaryModel)
            .values(
                vehicle_id=summary.vehicle_id,
                summary_date=summary.summary_date,
                start_latitude=summary.start_latitude,
                start_longitude=summary.start_longitude,
                end_latitude=summary.end_latitude,
                end_longitude=summary.end_longitude,
                total_distance_km=summary.total_distance_km,
                total_operational_hours=summary.total_operational_hours,
                trip_count=summary.trip_count,
                fuel_consumed_liters=summary.fuel_consumed_liters,
            )
            .on_conflict_do_update(
                index_elements=["vehicle_id", "summary_date"],
                set_={
                    "end_latitude": summary.end_latitude,
                    "end_longitude": summary.end_longitude,
                    "total_distance_km": summary.total_distance_km,
                    "total_operational_hours": summary.total_operational_hours,
                    "trip_count": summary.trip_count,
                    "fuel_consumed_liters": summary.fuel_consumed_liters,
                },
            )
        )
        await db.execute(stmt)
        await db.commit()

    async def fetch_with_date_range(
        self,
        db_session: AsyncSession,
        date_start: date,
        date_end: date,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        report_by: str,
    ) -> Tuple[List[DailyVehicleSummary], int]:
        try:
            # Safety check for dynamic column access
            if (
                not hasattr(DailyVehicleSummaryModel, sort_by)
                and sort_by != "utilization_score_primary"
            ):
                raise ValueError(f"Invalid sort_by field: {sort_by}")

            elif sort_by == "utilization_score_primary":
                if report_by == "distance":
                    sort_column = "total_distance_km"
                elif report_by == "hours":
                    sort_column = "total_operational_hours"
            else:
                sort_column = sort_by

            order = desc if sort_order.lower() == "desc" else asc

            # Main query with pagination
            stmt = (
                select(DailyVehicleSummaryModel)
                .where(DailyVehicleSummaryModel.summary_date >= date_start)
                .where(DailyVehicleSummaryModel.summary_date <= date_end)
                .order_by(order(sort_column))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )

            result = await db_session.execute(stmt)
            items = result.scalars().all()

            # Total count query
            count_stmt = (
                select(func.count())
                .select_from(DailyVehicleSummaryModel)
                .where(DailyVehicleSummaryModel.summary_date >= date_start)
                .where(DailyVehicleSummaryModel.summary_date <= date_end)
            )
            count_result = await db_session.execute(count_stmt)
            total_count = cast(int, count_result.scalar_one())

            # Convert ORM to DTO
            items_dto = [
                DailyVehicleSummary.model_validate(item.__dict__) for item in items
            ]

            return items_dto, total_count

        except SQLAlchemyError as e:
            logger.error("Database error: %s", str(e), exc_info=True)
            raise RuntimeError(
                "Failed to fetch asset summaries due to a database error."
            ) from e

        except Exception as e:
            logger.error("Unexpected error: %s", str(e), exc_info=True)
            raise RuntimeError(
                "Unexpected error while fetching asset summaries."
            ) from e
