import logging
from datetime import datetime
from http import HTTPStatus

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Query
from src.fastapi.database.database import db
from src.fastapi.gps_devices.exceptions import (
    GPSDeviceNotFoundException,
    GPSException,
    GPSInvalidDateException,
    GPSNotFoundException,
)
from src.fastapi.gps_devices.schemas import GPSStatsResponse
from src.fastapi.gps_devices.services import GpsStatsService
from src.fastapi.middleware.auth import validate_api_key
from src.fastapi.rabbitmq_handlers.gps.repositories import GpsEventRepository

logger = logging.getLogger(__name__)
gps_router = APIRouter(prefix="/gps_devices", tags=["GPS Devices"])

# create service with injected repository
gps_stats_service = GpsStatsService(GpsEventRepository())


@gps_router.get(
    "/{device_id}", response_model=GPSStatsResponse, status_code=HTTPStatus.OK
)
async def get_vehicle_stats(
    device_id: str,
    date: str = Query(
        ..., description="Date in YYYY-MM-DD format", pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    session: AsyncSession = Depends(db.get_client),
    _: str = Depends(validate_api_key),
):
    logger.info(f"Request stats for {device_id} on {date}")
    try:
        day = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        logger.error("Invalid date format: %s", date)
        raise GPSInvalidDateException(date)

    try:
        result = await gps_stats_service.calculate_stats(session, device_id, day)
        return GPSStatsResponse(**result)
    except (GPSNotFoundException, GPSDeviceNotFoundException) as e:
        logger.error("Error: %s", e)
        raise e
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        raise GPSException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, message=str(e))
