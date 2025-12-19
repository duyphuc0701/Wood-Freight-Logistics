import hashlib
import json
import logging
from functools import wraps

from src.fastapi.redis.redis import redis_manager

logger = logging.getLogger(__name__)


def cache_api_call(cache_key_prefix: str, ttl: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if redis_manager.redis_client is None:
                logger.error("Redis client is not initialized")
                return await func(*args, **kwargs)
            cache_key = (
                f"{cache_key_prefix}:"
                f"{hashlib.md5(json.dumps(args, sort_keys=True)
                               .encode()).hexdigest()}"
            )
            try:
                cached_result = await redis_manager.redis_client.get(cache_key)
                if cached_result:
                    logger.info(f"Cache hit for {cache_key}")
                    return json.loads(cached_result)
            except Exception as e:
                logger.error(f"Failed to get from Redis: {str(e)}")
            result = await func(*args, **kwargs)
            if result:
                try:
                    await redis_manager.redis_client.setex(
                        cache_key, ttl, json.dumps(result)
                    )
                    logger.info(f"Cached result for {cache_key}")
                except Exception as e:
                    logger.error(f"Failed to cache to Redis: {str(e)}")
            return result

        return wrapper

    return decorator
