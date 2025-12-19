import json
from unittest.mock import AsyncMock, patch

from src.fastapi.redis.decorators import cache_api_call
from src.fastapi.redis.redis import RedisManager, redis_manager


# Dummy function to wrap
@cache_api_call("test_prefix", ttl=60)
async def dummy_function(x, y):
    return {"result": x + y}


async def test_cache_disabled_when_redis_not_initialized():
    redis_manager.redis_client = None
    result = await dummy_function(1, 2)
    assert result == {"result": 3}


async def test_cache_hit(monkeypatch):
    mock_redis = AsyncMock()
    cached_value = json.dumps({"result": 42})
    mock_redis.get.return_value = cached_value
    redis_manager.redis_client = mock_redis

    result = await dummy_function(1, 2)
    assert result == {"result": 42}
    mock_redis.get.assert_awaited()
    mock_redis.setex.assert_not_called()


async def test_cache_miss(monkeypatch):
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Simulate cache miss
    redis_manager.redis_client = mock_redis

    result = await dummy_function(3, 4)
    assert result == {"result": 7}
    mock_redis.get.assert_awaited()
    mock_redis.setex.assert_awaited()


async def test_redis_get_raises_error(monkeypatch):
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("Redis get failed")
    redis_manager.redis_client = mock_redis

    result = await dummy_function(2, 3)
    assert result == {"result": 5}
    mock_redis.setex.assert_awaited()


async def test_redis_set_raises_error(monkeypatch):
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.setex.side_effect = Exception("Redis set failed")
    redis_manager.redis_client = mock_redis

    result = await dummy_function(4, 5)
    assert result == {"result": 9}
    mock_redis.get.assert_awaited()
    mock_redis.setex.assert_awaited()


@patch("src.fastapi.redis.redis.get_settings")
@patch("src.fastapi.redis.redis.redis.Redis", new_callable=AsyncMock)
async def test_init_redis(mock_redis_class, mock_get_settings):
    mock_get_settings.return_value.REDIS_HOST = "localhost"
    mock_get_settings.return_value.REDIS_PORT = 6379

    manager = RedisManager()
    await manager.init_redis()

    mock_redis_class.assert_awaited_once_with(
        host="localhost", port=6379, encoding="utf-8", decode_responses=True
    )
    assert manager.redis_client is not None


async def test_close_redis():
    mock_client = AsyncMock()
    manager = RedisManager()
    manager.redis_client = mock_client

    await manager.close_redis()

    mock_client.aclose.assert_awaited_once()
    assert manager.redis_client is None
