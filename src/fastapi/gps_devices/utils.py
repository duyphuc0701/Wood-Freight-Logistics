import logging
from datetime import datetime, timedelta

from sqlalchemy import select, type_coerce
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import sqltypes

from src.fastapi.gps_devices.exceptions import (
    GPSDeviceNotFoundException,
    GPSNotFoundException,
    GPSStatsException,
)
from src.fastapi.rabbitmq_handlers.gps.models import GPSEventModel

logger = logging.getLogger(__name__)


async def calculate_vehicle_stats(
    db: AsyncSession, device_id: str, date: datetime
) -> dict:
    """Calculate total distance, average speed, and miles for a device in a day."""
    try:
        # Check if device_id exists in the database
        device_exists_query = (
            select(GPSEventModel).where(GPSEventModel.device_id == device_id).limit(1)
        )
        device_exists_result = await db.execute(device_exists_query)
        if not device_exists_result.scalars().first():
            logger.warning(f"Device ID {device_id} does not exist in the database")
            raise GPSDeviceNotFoundException(device_id)

        # Query GPS events for the specified day
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        query = select(GPSEventModel).where(
            GPSEventModel.device_id == device_id,
            type_coerce(GPSEventModel.timestamp, sqltypes.DateTime) >= start_of_day,
            type_coerce(GPSEventModel.timestamp, sqltypes.DateTime) < end_of_day,
        )
        result = await db.execute(query)
        events = result.scalars().all()

        if not events:
            logger.warning(
                f"No GPS events found for device {device_id} " f"on {date.date()}"
            )
            raise GPSNotFoundException(device_id, date.date().isoformat())

        # Assume odometer is cumulative
        sorted_events = sorted(events, key=lambda x: x.timestamp)
        total_distance_km = (
            sorted_events[-1].odometer - sorted_events[0].odometer
            if len(sorted_events) > 1
            else 0
        )
        total_distance_km = total_distance_km
        avg_speed = sum(event.speed for event in events) / len(events) if events else 0
        total_distance_miles = total_distance_km * 0.621371

        return {
            "device_id": device_id,
            "date": date.date().isoformat(),
            "total_distance_km": total_distance_km,
            "total_distance_miles": total_distance_miles,
            "average_speed": avg_speed,
        }
    except (GPSNotFoundException, GPSDeviceNotFoundException) as e:
        raise e
    except Exception as e:
        logger.error(f"Stats calculation error: {str(e)}")
        raise GPSStatsException(device_id, date.date().isoformat(), str(e))
