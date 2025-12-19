import json
import logging
from datetime import date, datetime
from typing import List, Optional

import pendulum

from src.fastapi.config import get_settings
from src.fastapi.daily_summary.schemas import DailyVehicleSummary
from src.fastapi.daily_summary.states import EngineState, get_state
from src.fastapi.daily_summary.strategies import (
    IOperationalHoursStrategy,
    ITripDefinitionStrategy,
)
from src.fastapi.daily_summary.utils import seconds_since_midnight
from src.fastapi.rabbitmq_handlers.gps.schemas import GPSEventResponse
from src.fastapi.redis.redis import redis_manager

settings = get_settings()
TIMEZONE = settings.TIMEZONE
HCMC_TZ = pendulum.timezone(TIMEZONE)

logger = logging.getLogger(__name__)


class DailyAggregator:
    def __init__(
        self,
        trip_strategy: ITripDefinitionStrategy,
        operational_hours_strategy: IOperationalHoursStrategy,
    ):
        self.trip_strategy = trip_strategy
        self.operational_hours_strategy = operational_hours_strategy
        self.saved_keys: List[str] = []

    async def process_event(self, event: GPSEventResponse):
        """
        Process a single GPS event, updating or initializing the daily summary.
        """
        try:
            cached_daily_summary = await self.get_cached_summary(
                event.device_id, event.timestamp.date()
            )
            if cached_daily_summary is None:
                cached_daily_summary = DailyVehicleSummary(
                    vehicle_id=event.device_id,
                    summary_date=event.timestamp.date(),
                    start_latitude=event.latitude,
                    start_longitude=event.longitude,
                    end_latitude=event.latitude,
                    end_longitude=event.longitude,
                    total_distance_km=0,
                    total_operational_hours=0,
                    trip_count=0,
                    fuel_consumed_liters=0,
                    odometer=event.odometer,
                    fuel_gauge=event.fuel_gauge,
                    last_moving_time=None,
                    last_event_time=event.timestamp,
                    state=EngineState.ENGINE_OFF,
                )
                await self.save_summary_to_cache(cached_daily_summary)
                return

            cached_daily_summary.end_latitude = event.latitude
            cached_daily_summary.end_longitude = event.longitude
            cached_daily_summary.total_distance_km += (
                event.odometer - cached_daily_summary.odometer
            )
            cached_daily_summary.fuel_consumed_liters += (
                cached_daily_summary.fuel_gauge - event.fuel_gauge
            )
            logger.info(
                f"Fuel consumed liters of vehicle {cached_daily_summary.vehicle_id}"
                f" is {cached_daily_summary.fuel_consumed_liters}"
            )
            cached_daily_summary.odometer = event.odometer
            cached_daily_summary.fuel_gauge = event.fuel_gauge
            cached_daily_summary.state = get_state(event.power_on, event.speed)

            # Detect trip and update summary
            daily_summary = self.trip_strategy.detect_trip(cached_daily_summary, event)
            cached_daily_summary = daily_summary
            cached_daily_summary.total_operational_hours = (
                self.operational_hours_strategy.update_operational_hours(
                    event, cached_daily_summary
                )
            )

            cached_daily_summary.last_event_time = event.timestamp

            # Save updated summary back to Redis
            await self.save_summary_to_cache(cached_daily_summary)
        except Exception as e:
            logger.exception(
                "Error processing event for device %s: %s", event.device_id, e
            )
            # Depending on desired failure mode, either re-raise or swallow
            raise

    def generate_key(self, vehicle_id: str, date: date) -> str:
        return f"summary:{vehicle_id}_{date}"

    async def save_summary_to_cache(self, daily_summary: DailyVehicleSummary):
        try:
            key = self.generate_key(
                daily_summary.vehicle_id, daily_summary.summary_date
            )
            if key not in self.saved_keys:
                self.saved_keys.append(key)
            summary_dict = daily_summary.model_dump()

            def custom_serializer(obj):
                if isinstance(obj, date):
                    return obj.isoformat()
                if isinstance(obj, EngineState):
                    return obj.value
                return None

            serialized = json.dumps(summary_dict, default=custom_serializer)
            now = datetime.now(HCMC_TZ)
            seconds_in_day = 86400  # Total seconds in a day
            seconds_elapsed = seconds_since_midnight(now)
            seconds_remaining = int(seconds_in_day - seconds_elapsed)

            await redis_manager.redis_client.setex(key, seconds_remaining, serialized)

            logger.info(f"Save to cache with key: {key}")
        except Exception as e:
            logger.exception("Failed to save summary for key %s: %s", key, e)
            raise

    async def get_cached_summary(
        self, vehicle_id: str, date: date
    ) -> Optional[DailyVehicleSummary]:
        key = self.generate_key(vehicle_id, date)
        cached_result = await redis_manager.redis_client.get(key)
        if cached_result:
            summary_dict = json.loads(cached_result)
            # convert dict back to model or Pydantic schema
            return DailyVehicleSummary(**summary_dict)
        return None
