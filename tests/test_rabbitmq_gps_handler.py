from datetime import datetime
from unittest.mock import AsyncMock, patch

import pendulum
import pytest
from tenacity import RetryError

from src.fastapi.rabbitmq_handlers.gps.exceptions import (
    GPSDatabaseException,
    GPSDeviceAPIException,
    GPSRateLimitException,
    GPSRedisException,
    GPSRedisNotInitializedException,
)
from src.fastapi.rabbitmq_handlers.gps.handler import handle_gps_event
from src.fastapi.rabbitmq_handlers.gps.models import GPSEventModel
from src.fastapi.rabbitmq_handlers.gps.schemas import GPSEventCreate, GPSEventResponse
from src.fastapi.rabbitmq_handlers.gps.utils import (
    cache_processed_key,
    check_duplicate_event,
    dispatch_alert_event,
    fetch_device_name,
    get_device_name,
    invalidate_device_cache,
    persist_gps_event,
    save_gps_event,
)
from src.fastapi.websocket.models import AlertEvent


# region Fixtures
@pytest.fixture
def gps_event_create():
    return GPSEventCreate(
        device_id="device_123",
        timestamp=pendulum.datetime(2024, 5, 20, 8, 30, tz="Asia/Bangkok"),
        latitude=10.7769,
        longitude=106.6959,
        odometer=1000.0,
        power_on=True,
        speed=0.0,
        fuel_gauge=100.0,
    )


@pytest.fixture
def gps_event_response():
    return GPSEventResponse(
        device_id="device_123",
        device_name="device_name",
        timestamp=pendulum.datetime(2024, 5, 20, 8, 30, tz="Asia/Bangkok"),
        latitude=10.7769,
        longitude=106.6959,
        odometer=1000.0,
        power_on=True,
        speed=0.0,
        fuel_gauge=100.0,
    )


@pytest.fixture
def db_session():
    return AsyncMock()


# endregion


@patch("src.fastapi.rabbitmq_handlers.gps.handler.decode_payload")
async def test_handle_gps_event_decode_error(mock_decode):
    mock_decode.return_value = {}

    db = AsyncMock()
    response = await handle_gps_event(db, "bad-payload")

    assert response == {}


@patch("src.fastapi.rabbitmq_handlers.gps.handler.decode_payload")
@patch("src.fastapi.rabbitmq_handlers.gps.handler.check_duplicate_event")
async def test_handle_gps_event_duplicate_event(mock_check_duplicate, mock_decode):
    mock_check_duplicate.return_value = {"error": "Duplicate event"}
    mock_decode.return_value = AsyncMock()

    db = AsyncMock()
    response = await handle_gps_event(db, "some-payload")

    assert response == {"error": "Duplicate event"}


@patch("src.fastapi.rabbitmq_handlers.gps.handler.decode_payload")
@patch("src.fastapi.rabbitmq_handlers.gps.handler.check_duplicate_event")
@patch("src.fastapi.rabbitmq_handlers.gps.handler.get_device_name")
async def test_handle_gps_event_get_device_name_error(
    mock_get_device_name, mock_check_duplicate, mock_decode
):
    mock_get_device_name.return_value = {"error": "Failed to fetch device name"}
    mock_decode.return_value = AsyncMock()
    mock_check_duplicate.return_value = None
    db = AsyncMock()
    response = await handle_gps_event(db, "some-payload")

    assert response == {"error": "Failed to fetch device name"}


@patch("src.fastapi.rabbitmq_handlers.gps.handler.decode_payload")
@patch("src.fastapi.rabbitmq_handlers.gps.handler.check_duplicate_event")
@patch("src.fastapi.rabbitmq_handlers.gps.handler.get_device_name")
@patch("src.fastapi.rabbitmq_handlers.gps.handler.GPSEventResponse")
@patch("src.fastapi.rabbitmq_handlers.gps.handler.cache_processed_key")
async def test_handle_gps_event_cache_error(
    mock_cache_processed_key,
    mock_gps_event,
    mock_get_device_name,
    mock_check_duplicate,
    mock_decode,
):
    mock_cache_processed_key.return_value = {"error": "Failed to cache key"}
    mock_gps_event.return_value = AsyncMock()
    mock_get_device_name.return_value = "Device Name"
    mock_decode.return_value = AsyncMock()
    mock_check_duplicate.return_value = None

    db = AsyncMock()
    response = await handle_gps_event(db, "payload")

    assert response == {"error": "Failed to cache key"}


@patch("src.fastapi.rabbitmq_handlers.gps.handler.decode_payload")
@patch("src.fastapi.rabbitmq_handlers.gps.handler.check_duplicate_event")
@patch("src.fastapi.rabbitmq_handlers.gps.handler.get_device_name")
@patch("src.fastapi.rabbitmq_handlers.gps.handler.GPSEventResponse")
@patch("src.fastapi.rabbitmq_handlers.gps.handler.cache_processed_key")
@patch("src.fastapi.rabbitmq_handlers.gps.handler.persist_gps_event")
@patch("src.fastapi.rabbitmq_handlers.gps.handler.dispatch_alert_event")
@patch("src.fastapi.daily_summary.aggregator.DailyAggregator.process_event")
@patch("src.fastapi.idling_hotspots.detector.IdlingEventDetector.process_event")
async def test_handle_gps_event_success(
    mock_idling_detector_process_event,
    mock_daily_summary_process_event,
    mock_dispatch_alert_event,
    mock_persist_gps_event,
    mock_cache_processed_key,
    mock_gps_event,
    mock_get_device_name,
    mock_check_duplicate,
    mock_decode,
):
    gps_event = AsyncMock()
    gps_event.device_id = "dev123"
    gps_event.timestamp = "2025-05-07T10:00:00"
    gps_event.speed = 80
    gps_event.odometer = 1200
    gps_event.power_on = True
    gps_event.fuel_gauge = 95.0
    mock_decode.return_value = gps_event

    mock_check_duplicate.return_value = None
    mock_get_device_name.return_value = "Device Name"
    mock_gps_event.return_value = GPSEventResponse(
        device_id="dev123",
        device_name="Device Name",
        timestamp=datetime(2025, 5, 7, 10, 0, 0),
        speed=80,
        odometer=1200,
        power_on=True,
        latitude=12.34,
        longitude=56.78,
        fuel_gauge=95.0,
    )
    mock_cache_processed_key.return_value = None
    mock_persist_gps_event.return_value = None
    mock_dispatch_alert_event.return_value = None
    mock_daily_summary_process_event.return_value = None
    mock_idling_detector_process_event.return_value = None

    db = AsyncMock()
    response = await handle_gps_event(db, "payload")

    assert response["device_id"] == "dev123"


@patch("aiohttp.ClientSession.get")
async def test_fetch_device_name_success(mock_get):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"name": "Test Device"}
    mock_get.return_value.__aenter__.return_value = mock_response

    device_name = await fetch_device_name("dev123")
    assert device_name == "Test Device"


@patch("aiohttp.ClientSession.get")
@patch("tenacity.wait_exponential.__call__", return_value=0.01)
async def test_fetch_device_name_rate_limit(_, mock_get):
    mock_response = AsyncMock()
    mock_response.status = 429
    mock_response.text.return_value = "Too many requests"
    mock_get.return_value.__aenter__.return_value = mock_response

    with pytest.raises(RetryError) as exc_info:
        await fetch_device_name("dev123")

    assert isinstance(exc_info.value.last_attempt.exception(), GPSRateLimitException)


@patch("aiohttp.ClientSession.get")
async def test_fetch_device_name_server_error(mock_get):
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text.return_value = "Internal Server Error"
    mock_get.return_value.__aenter__.return_value = mock_response

    with pytest.raises(GPSDeviceAPIException) as e:
        await fetch_device_name("dev123")
    assert "500" in str(e.value)


@patch("aiohttp.ClientSession.get")
async def test_fetch_device_name_other_error(mock_get):
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_response.text.return_value = "Not found"
    mock_get.return_value.__aenter__.return_value = mock_response

    with pytest.raises(GPSDeviceAPIException):
        await fetch_device_name("dev123")


@patch("src.fastapi.rabbitmq_handlers.gps.utils.redis_manager")
async def test_invalidate_device_cache_success(mock_redis_manager):
    mock_redis_manager.redis_client = AsyncMock()
    mock_redis_manager.redis_client.delete = AsyncMock()
    await invalidate_device_cache("dev123")
    mock_redis_manager.redis_client.delete.assert_called_once()


@patch("src.fastapi.rabbitmq_handlers.gps.utils.redis_manager")
async def test_invalidate_device_cache_redis_exception(mock_redis_manager):
    mock_redis_manager.redis_client = AsyncMock()
    mock_redis_manager.redis_client.delete.side_effect = Exception("Redis fail")

    with pytest.raises(GPSRedisException):
        await invalidate_device_cache("dev123")


@patch("src.fastapi.rabbitmq_handlers.gps.utils.redis_manager")
async def test_invalidate_device_cache_no_client(mock_redis_manager):
    mock_redis_manager.redis_client = None

    with pytest.raises(GPSRedisNotInitializedException):
        await invalidate_device_cache("dev123")


@patch("src.fastapi.redis.redis.redis_manager.redis_client", new_callable=AsyncMock)
async def test_check_duplicate_event_no_duplicate(mock_redis_client, gps_event_create):
    mock_redis_client.setnx.return_value = True
    result = await check_duplicate_event(gps_event_create)

    assert result is None
    mock_redis_client.setnx.assert_called_once_with(
        f"gps_event:{gps_event_create.device_id}:{gps_event_create.timestamp}",
        "processed",
    )


@patch("src.fastapi.redis.redis.redis_manager.redis_client", new_callable=AsyncMock)
async def test_check_duplicate_event_duplicate(mock_redis_client, gps_event_create):
    mock_redis_client.setnx.return_value = False
    result = await check_duplicate_event(gps_event_create)

    assert result == {"error": "Duplicate event"}


@patch("src.fastapi.redis.redis.redis_manager.redis_client", None)
async def test_check_duplicate_event_redis_not_initialized(gps_event_create):
    result = await check_duplicate_event(gps_event_create)

    assert result == {"error": str(GPSRedisNotInitializedException("check_duplicate"))}


@patch("src.fastapi.redis.redis.redis_manager.redis_client", new_callable=AsyncMock)
async def test_check_duplicate_event_redis_error(mock_redis_client, gps_event_create):
    mock_redis_client.setnx.side_effect = Exception("Redis error")
    result = await check_duplicate_event(gps_event_create)

    assert isinstance(result, dict)


@patch(
    "src.fastapi.rabbitmq_handlers.gps.utils.fetch_device_name", new_callable=AsyncMock
)
async def test_get_device_name_success(mock_fetch_device_name):
    mock_fetch_device_name.return_value = "device_name"
    result = await get_device_name("device_123")

    assert result == "device_name"
    mock_fetch_device_name.assert_called_once_with("device_123")


@patch(
    "src.fastapi.rabbitmq_handlers.gps.utils.fetch_device_name", new_callable=AsyncMock
)
async def test_get_device_name_not_found(mock_fetch_device_name):
    mock_fetch_device_name.return_value = None
    result = await get_device_name("device_123")

    assert result == {"error": str(GPSDeviceAPIException("device_123"))}


@patch("src.fastapi.redis.redis.redis_manager.redis_client", new_callable=AsyncMock)
async def test_cache_processed_key_success(mock_redis_client):
    key = "gps_event:device_123:2024-05-20T08:30:00+07:00"
    result = await cache_processed_key(key)

    assert result is None
    mock_redis_client.setex.assert_called_once_with(key, 3600, "processed")


@patch("src.fastapi.redis.redis.redis_manager.redis_client", new_callable=AsyncMock)
async def test_cache_processed_key_redis_error(mock_redis_client):
    key = "gps_event:device_123:2024-05-20T08:30:00+07:00"
    mock_redis_client.setex.side_effect = Exception("Redis error")
    result = await cache_processed_key(key)

    assert isinstance(result, dict)


@patch(
    "src.fastapi.rabbitmq_handlers.gps.handler.gps_repo.save", new_callable=AsyncMock
)
async def test_persist_gps_event_success(
    mock_gps_repo_save, db_session, gps_event_response
):
    await persist_gps_event(db_session, gps_event_response)

    mock_gps_repo_save.assert_called_once_with(db_session, gps_event_response)


@patch(
    "src.fastapi.rabbitmq_handlers.gps.handler.gps_repo.save", new_callable=AsyncMock
)
async def test_persist_gps_event_error(
    mock_gps_repo_save, db_session, gps_event_response
):
    mock_gps_repo_save.side_effect = Exception("Database error")
    with pytest.raises(Exception):
        await persist_gps_event(db_session, gps_event_response)


@patch(
    "src.fastapi.rabbitmq_handlers.gps.utils.send_alert_event", new_callable=AsyncMock
)
async def test_dispatch_alert_event_success(
    mock_send_alert_event, gps_event_create, gps_event_response
):
    device_name = "device_name"
    await dispatch_alert_event(gps_event_create, device_name, gps_event_response)

    mock_send_alert_event.assert_called_once()
    alert = mock_send_alert_event.call_args[0][0]
    assert isinstance(alert, AlertEvent)
    assert alert.event_type == "gps"
    assert alert.device_id == gps_event_create.device_id
    assert alert.device_name == device_name
    assert alert.timestamp == gps_event_create.timestamp


@patch(
    "src.fastapi.rabbitmq_handlers.gps.utils.send_alert_event", new_callable=AsyncMock
)
async def test_dispatch_alert_event_error(
    mock_send_alert_event, gps_event_create, gps_event_response
):
    mock_send_alert_event.side_effect = Exception("WebSocket error")
    await dispatch_alert_event(gps_event_create, "device_name", gps_event_response)

    mock_send_alert_event.assert_called_once()


async def test_save_gps_event_success(db_session, gps_event_response):
    db_session.commit = AsyncMock()
    db_session.refresh = AsyncMock()

    result = await save_gps_event(db_session, gps_event_response)

    assert isinstance(result, GPSEventModel)
    assert result.device_id == gps_event_response.device_id
    assert result.device_name == gps_event_response.device_name
    assert result.timestamp == gps_event_response.timestamp
    db_session.commit.assert_called_once()
    db_session.refresh.assert_called_once()


async def test_save_gps_event_database_error(db_session, gps_event_response):
    db_session.commit = AsyncMock(side_effect=Exception("Database error"))
    db_session.rollback = AsyncMock()

    with pytest.raises(GPSDatabaseException):
        await save_gps_event(db_session, gps_event_response)

    db_session.rollback.assert_called_once()
