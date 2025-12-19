import logging

import redis.asyncio as redis

from src.fastapi.config import get_settings

logger = logging.getLogger(__name__)


class RedisManager:
    def __init__(self):
        self.redis_client = None

    async def init_redis(self):
        """Initialize Redis connection"""
        self.redis_client = await redis.Redis(
            host=get_settings().REDIS_HOST,
            port=get_settings().REDIS_PORT,
            encoding="utf-8",
            decode_responses=True,
        )
        self.redis_client.config_set("notify-keyspace-events", "Ex")
        logger.info("Redis connection initialized")

    async def close_redis(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.aclose()
            logger.info("Redis connection closed")
            self.redis_client = None


redis_manager = RedisManager()
