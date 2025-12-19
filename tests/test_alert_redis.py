from unittest.mock import AsyncMock, patch

import pytest

from src.alert.redis.redis import RedisManager


@pytest.mark.asyncio
@patch("src.alert.redis.redis.redis.Redis", new_callable=AsyncMock)
async def test_init_redis(mock_redis_class):
    # Arrange
    mock_redis_instance = AsyncMock()
    mock_redis_class.return_value = mock_redis_instance
    manager = RedisManager()

    # Act
    await manager.init_redis()

    # Assert
    mock_redis_class.assert_called_once_with(
        host=mock_redis_class.call_args.kwargs["host"],
        port=mock_redis_class.call_args.kwargs["port"],
        encoding="utf-8",
        decode_responses=True,
    )
    assert manager.redis_client is mock_redis_instance


@pytest.mark.asyncio
async def test_close_redis():
    # Arrange
    manager = RedisManager()
    mock_client = AsyncMock()
    manager.redis_client = mock_client

    # Act
    await manager.close_redis()

    # Assert
    mock_client.aclose.assert_awaited_once()
    assert manager.redis_client is None


@pytest.mark.asyncio
async def test_close_redis_noop_if_none():
    # Arrange
    manager = RedisManager()
    manager.redis_client = None

    # Act
    await manager.close_redis()

    # Assert
    assert manager.redis_client is None
