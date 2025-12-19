import logging
from datetime import datetime

import aiohttp
from aiohttp import ClientResponseError
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.fastapi.config import get_settings
from src.fastapi.rabbitmq_handlers.fault.exceptions import (
    FaultDatabaseSaveException,
    FaultLabelAPIException,
    FaultRateLimitException,
)
from src.fastapi.rabbitmq_handlers.fault.models import FaultEventModel
from src.fastapi.rabbitmq_handlers.fault.schemas import FaultEventResponse
from src.fastapi.redis.decorators import cache_api_call
from src.fastapi.redis.redis import redis_manager

logger = logging.getLogger(__name__)
settings = get_settings()
DEVICE_API_URL = get_settings().DEVICE_API_URL
FAULT_API_URL = get_settings().FAULT_API_URL


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((FaultLabelAPIException, ClientResponseError)),
)
@cache_api_call(cache_key_prefix="fault_label", ttl=300)
async def fetch_fault_label(fault_code: str) -> str:
    """
    Fetch the human-readable label for a fault code via aiohttp
    """
    url = f"{FAULT_API_URL}/{fault_code}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            logger.info(f"Fetching fault label for code {fault_code} from {url}")

            if response.status == 200:
                data = await response.json()

                # Explicitly narrow and coerce into a str
                if isinstance(data, list) and data:
                    raw = data[0].get("label", None)
                    label: str = raw if isinstance(raw, str) else "Unknown"

                elif isinstance(data, dict):
                    raw = data.get("label", None)
                    label = raw if isinstance(raw, str) else "Unknown"

                else:
                    label = "Unknown"

                logger.info(f"Fault label: {label}")
                return label

            elif response.status == 429:
                logger.warning(f"Rate limit exceeded for fault code {fault_code}")
                raise FaultRateLimitException(fault_code)

            elif response.status >= 500:
                text = await response.text()
                logger.error(f"Server error for fault code {fault_code}: {text}")
                raise FaultLabelAPIException(fault_code)

            else:
                logger.error(f"Failed to fetch fault label, status: {response.status}")
                raise FaultLabelAPIException(fault_code)


async def save_fault_event(
    db: AsyncSession, fault_event: FaultEventResponse
) -> FaultEventModel:
    """
    Create a new Fault event in the database.
    """
    logger.info(
        f"Saving Fault event for device={fault_event.device_id} "
        f"label={fault_event.fault_label}"
    )
    try:
        new_event = FaultEventModel(**fault_event.model_dump())
        db.add(new_event)
        await db.commit()
        await db.refresh(new_event)
        logger.info(f"Fault event created with ID: {new_event.id}")
        return new_event

    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating Fault event: {e}")
        raise FaultDatabaseSaveException(
            device_id=fault_event.device_id, fault_code=fault_event.fault_code
        )


async def cache_fault_segment(
    device_id: str,
    fault_code: str,
    timestamp: datetime,
    sequence: int,
    fault_bits: str,
    expire_secs: int = 3600,
) -> int:
    """
    Store one segment of a multi-part fault in Redis.
    Returns the total number of parts now stored.
    """
    key = f"fault_parts:{device_id}:{fault_code}:{timestamp}"
    try:
        # HSET sequence → bit-string
        await redis_manager.redis_client.hset(key, sequence, fault_bits)
        # Ensure key auto-expires
        await redis_manager.redis_client.expire(key, expire_secs)
        # Count how many segments we have so far
        count_any = await redis_manager.redis_client.hlen(key)
        count = int(count_any)
        return count
    except Exception as e:
        logger.error(f"[{device_id}] Redis aggregation error: {e}")
        raise


async def assemble_all_fault_segments(
    device_id: str, fault_code: str, timestamp: datetime, total_number: int
) -> tuple[str, bytes]:
    """
    Once all parts have arrived, pull them out of Redis, reconstruct:
      - the concatenated bit-string
      - the raw bytes payload
    Deletes the Redis key before returning.
    """
    key = f"fault_parts:{device_id}:{fault_code}:{timestamp}"
    try:
        raw_map = await redis_manager.redis_client.hgetall(key)
        # raw_map: {b"0": b"01010101", b"1": b"10101010", ...}
        seq_to_bits = {
            int(k.decode() if isinstance(k, bytes) else k): (
                v.decode() if isinstance(v, bytes) else v
            )
            for k, v in raw_map.items()
        }
        ordered_bits = [seq_to_bits[i] for i in range(total_number)]
        bitstring = "".join(ordered_bits)
        # pack each 8-bit substring into a byte
        payload_bytes = bytes(int(ordered_bits[i], 2) for i in range(total_number))
        return bitstring, payload_bytes
    except Exception as e:
        logger.error(f"[{device_id}] Error reconstructing fault payload: {e}")
        raise
    finally:
        # remove the temporary aggregation data
        await redis_manager.redis_client.delete(key)
