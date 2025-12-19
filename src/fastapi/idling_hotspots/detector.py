import json
import logging
from datetime import datetime
from typing import Optional, cast

from sqlalchemy.ext.asyncio import AsyncSession

from src.fastapi.idling_hotspots.repositories.idling_data import IdlingDataRepository
from src.fastapi.idling_hotspots.schemas import IdlingDetectedEvent
from src.fastapi.rabbitmq_handlers.gps.schemas import GPSEventResponse
from src.fastapi.redis.redis import redis_manager

logger = logging.getLogger(__name__)

idling_repo: IdlingDataRepository = IdlingDataRepository()


class IdlingEventDetector:
    async def process_event(self, db_session: AsyncSession, event: GPSEventResponse):
        idling_event = await self.get_saved_idling_events_from_cache(event.device_id)
        if event.power_on and event.speed == 0:
            logger.info(f"Vehicle {event.device_id} starts idling")
            # Device is idling
            if not idling_event:
                # Create a new idling event
                idling_event = IdlingDetectedEvent(
                    device_id=event.device_id,
                    start_time=event.timestamp,
                    end_time=event.timestamp,
                    latitude=event.latitude,
                    longitude=event.longitude,
                )
            idling_event.end_time = event.timestamp
            await self.save_idling_event_to_cache(event.device_id, idling_event)
        else:
            logger.info("abcdxyz")
            if idling_event:
                logger.info(f"Vehicle {event.device_id} is no longer idling")
                # Device is no longer idling, save the event
                await idling_repo.save_idling_event(
                    db_session=db_session, idling_event=idling_event
                )
                # Clear the saved idling event
                await self.clear_idling_event_cache(event.device_id)

    def idling_key(self, device_id: str) -> str:
        return f"idling_events:{device_id}"

    async def get_saved_idling_events_from_cache(
        self, device_id: str
    ) -> Optional[IdlingDetectedEvent]:
        key = self.idling_key(device_id)
        saved_event_str = await redis_manager.redis_client.get(key)
        if saved_event_str:
            logger.info(f"Found cached idling of vehicle {device_id}")
            saved_event = json.loads(saved_event_str)
            return cast(
                IdlingDetectedEvent, IdlingDetectedEvent.model_validate(saved_event)
            )
        return None

    async def save_idling_event_to_cache(
        self, device_id: str, event: IdlingDetectedEvent
    ):
        key = self.idling_key(device_id)

        def custom_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return None

        serialized = json.dumps(event.model_dump(), default=custom_serializer)
        await redis_manager.redis_client.set(key, serialized)
        logger.info(f"Save idling event to cache with key: {key}")

    async def clear_idling_event_cache(self, device_id: str):
        key = self.idling_key(device_id)
        await redis_manager.redis_client.delete(key)
        logger.info(f"Clear idling event from cache with key: {key}")
