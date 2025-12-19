import logging
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from src.fastapi.daily_summary.aggregator import DailyAggregator
from src.fastapi.daily_summary.strategies import (
    DefaultOperationalHoursStrategy,
    DefaultTripDefinitionStrategy,
    IOperationalHoursStrategy,
    ITripDefinitionStrategy,
)
from src.fastapi.idling_hotspots.detector import IdlingEventDetector
from src.fastapi.rabbitmq_handlers.gps.repositories import (
    GpsEventRepository,
    IGpsEventRepository,
)
from src.fastapi.rabbitmq_handlers.gps.schemas import GPSEventResponse
from src.fastapi.rabbitmq_handlers.gps.utils import (
    cache_processed_key,
    check_duplicate_event,
    decode_payload,
    dispatch_alert_event,
    get_device_name,
    persist_gps_event,
)

logger = logging.getLogger(__name__)
gps_repo: IGpsEventRepository = GpsEventRepository()
trip_strategy: ITripDefinitionStrategy = DefaultTripDefinitionStrategy()
operational_hours_strategy: IOperationalHoursStrategy = (
    DefaultOperationalHoursStrategy()
)
daily_aggregator: DailyAggregator = DailyAggregator(
    trip_strategy, operational_hours_strategy
)
idling_detector: IdlingEventDetector = IdlingEventDetector()


async def handle_gps_event(db: AsyncSession, payload: str) -> dict:
    gps_event_or_error = await decode_payload(payload)
    if isinstance(gps_event_or_error, dict):
        return gps_event_or_error
    gps_event = gps_event_or_error

    duplicate_check = await check_duplicate_event(gps_event)
    if duplicate_check:
        return duplicate_check

    key = f"gps_event:{gps_event.device_id}:{gps_event.timestamp}"

    device_name_or_error = await get_device_name(gps_event.device_id)
    if isinstance(device_name_or_error, dict):
        return device_name_or_error
    device_name = device_name_or_error

    response = GPSEventResponse(
        device_id=gps_event.device_id,
        device_name=device_name,
        timestamp=gps_event.timestamp,
        speed=gps_event.speed,
        odometer=gps_event.odometer,
        power_on=gps_event.power_on,
        latitude=gps_event.latitude,
        longitude=gps_event.longitude,
        fuel_gauge=gps_event.fuel_gauge,
    )

    cache_error = await cache_processed_key(key)
    if cache_error:
        return cache_error

    await persist_gps_event(db, response)

    await dispatch_alert_event(gps_event, device_name, response)

    await daily_aggregator.process_event(response)

    await idling_detector.process_event(db, response)

    return cast(dict, response.model_dump())
