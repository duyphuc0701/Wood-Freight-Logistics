import hashlib
import json
import logging
from typing import Optional

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.fastapi.config import get_settings
from src.fastapi.rabbitmq_handlers.gps.exceptions import (
    GPSDatabaseException,
    GPSDeviceAPIException,
    GPSRateLimitException,
    GPSRedisException,
    GPSRedisNotInitializedException,
)
from src.fastapi.rabbitmq_handlers.gps.models import GPSEventModel
from src.fastapi.rabbitmq_handlers.gps.schemas import GPSEventCreate, GPSEventResponse
from src.fastapi.redis.decorators import cache_api_call
from src.fastapi.redis.redis import redis_manager
from src.fastapi.websocket.client import send_alert_event
from src.fastapi.websocket.models import AlertEvent

logger = logging.getLogger(__name__)
settings = get_settings()
DEVICE_API_URL = get_settings().DEVICE_API_URL


async def decode_payload(payload: str) -> GPSEventCreate:
    return GPSEventCreate.from_base64(payload)


async def check_duplicate_event(gps_event: GPSEventCreate) -> dict | None:
    if redis_manager.redis_client is None:
        logger.error("Redis client is not initialized")
        return {"error": str(GPSRedisNotInitializedException("check_duplicate"))}

    key = f"gps_event:{gps_event.device_id}:{gps_event.timestamp}"
    try:
        if not await redis_manager.redis_client.setnx(key, "processed"):
            logger.info(
                "Duplicate event: %s at %s", gps_event.device_id, gps_event.timestamp
            )
            return {"error": "Duplicate event"}
    except Exception as e:
        logger.error(f"Redis error: {e}")
        return {"error": str(GPSRedisException("setnx", key, str(e)))}
    return None


async def get_device_name(device_id: str) -> str | dict:
    try:
        device_name = await fetch_device_name(device_id)
        if not device_name:
            raise GPSDeviceAPIException(device_id)
        return str(device_name)
    except GPSDeviceAPIException as e:
        logger.error(f"Device API error: {e}")
        return {"error": str(e)}


async def cache_processed_key(key: str) -> dict | None:
    try:
        await redis_manager.redis_client.setex(key, 3600, "processed")
    except Exception as e:
        logger.error(f"Redis cache error: {e}")
        return {"error": str(GPSRedisException("setex", key, str(e)))}
    return None


async def persist_gps_event(db: AsyncSession, response: GPSEventResponse) -> None:
    try:
        from src.fastapi.rabbitmq_handlers.gps.handler import gps_repo

        await gps_repo.save(db, response)
    except Exception as e:
        logger.error(f"Error saving GPS event: {e}")
        raise e


async def dispatch_alert_event(
    gps_event: GPSEventCreate, device_name: str, response: GPSEventResponse
) -> None:
    alert = AlertEvent(
        event_type="gps",
        device_id=gps_event.device_id,
        device_name=device_name,
        timestamp=gps_event.timestamp,
        data=response.model_dump(),
    )
    try:
        await send_alert_event(alert)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


# API calls
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((GPSRateLimitException, aiohttp.ClientResponseError)),
)
@cache_api_call(cache_key_prefix="device_name", ttl=300)
async def fetch_device_name(device_id: str) -> Optional[str]:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{DEVICE_API_URL}/{device_id}") as response:
            logger.info(f"Fetching {device_id} from {DEVICE_API_URL}")
            if response.status == 200:
                data = await response.json()
                return str(data.get("name", ""))
            elif response.status == 429:
                logger.warning(f"Rate limit exceeded for device {device_id}")
                raise GPSRateLimitException(device_id)
            elif response.status == 500:
                logger.error(
                    f"Server error for device {device_id}: " f"{await response.text()}"
                )
                raise GPSDeviceAPIException(
                    device_id, response.status, await response.text()
                )
            else:
                logger.error(
                    f"Failed to fetch device name for {device_id}, "
                    f"status: {response.status}"
                )
                raise GPSDeviceAPIException(device_id, response.status)


async def invalidate_device_cache(device_id: str):
    cache_key = f"device_name:{hashlib.md5(
        json.dumps([device_id], sort_keys=True).encode()).hexdigest()}"

    if not redis_manager.redis_client:
        logger.error("Redis client is not initialized")
        raise GPSRedisNotInitializedException("invalidate_cache")

    try:
        await redis_manager.redis_client.delete(cache_key)
        logger.info(f"Invalidated cache for device {device_id}")
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {str(e)}")
        raise GPSRedisException("delete", cache_key, str(e))


async def save_gps_event(
    db: AsyncSession, gps_response: GPSEventResponse
) -> GPSEventModel:
    """Create a new GPS event in the database."""
    logger.info(f"Saving GPS event for device: {gps_response.device_id}")
    try:
        new_event = GPSEventModel(
            device_id=gps_response.device_id,
            device_name=gps_response.device_name,
            timestamp=gps_response.timestamp,
            speed=gps_response.speed,
            odometer=gps_response.odometer,
            power_on=gps_response.power_on,
            latitude=gps_response.latitude,
            longitude=gps_response.longitude,
        )
        db.add(new_event)
        await db.commit()
        await db.refresh(new_event)
        logger.info(f"GPS event created with ID: {new_event.id}")
        return new_event
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating GPS event: {str(e)}")
        raise GPSDatabaseException(
            gps_response.device_id, str(gps_response.timestamp), str(e)
        )
