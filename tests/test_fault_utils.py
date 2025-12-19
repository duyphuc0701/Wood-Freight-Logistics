from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tenacity import RetryError

from src.fastapi.rabbitmq_handlers.fault.exceptions import (
    FaultDatabaseSaveException,
    FaultLabelAPIException,
    FaultRateLimitException,
)
from src.fastapi.rabbitmq_handlers.fault.models import FaultEventModel
from src.fastapi.rabbitmq_handlers.fault.schemas import FaultEventResponse
from src.fastapi.rabbitmq_handlers.fault.utils import (
    assemble_all_fault_segments,
    cache_fault_segment,
    fetch_fault_label,
    save_fault_event,
)


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get")
async def test_fetch_fault_label_success_dict(mock_get):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"label": "Overheat"}
    mock_get.return_value.__aenter__.return_value = mock_response

    result = await fetch_fault_label("1")
    assert result == "Overheat"


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get")
async def test_fetch_fault_label_unknown_label(mock_get):
    mock_response = AsyncMock()
    mock_response.status = 200
    # label is not a string
    mock_response.json.return_value = {"label": 1234}
    mock_get.return_value.__aenter__.return_value = mock_response

    result = await fetch_fault_label("1")
    assert result == "Unknown"


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get")
@patch("tenacity.wait_exponential.__call__", return_value=0.01)
async def test_fetch_fault_label_rate_limit(_, mock_get):
    mock_response = AsyncMock()
    mock_response.status = 429
    mock_response.text.return_value = "Too many requests"
    mock_get.return_value.__aenter__.return_value = mock_response

    with pytest.raises(RetryError) as exc_info:
        await fetch_fault_label("12")

    assert isinstance(exc_info.value.last_attempt.exception(), FaultRateLimitException)


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get")
@patch("tenacity.wait_exponential.__call__", return_value=0.01)
async def test_fetch_fault_label_server_error(_, mock_get):
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text.return_value = "Internal Server Error"
    mock_get.return_value.__aenter__.return_value = mock_response

    with pytest.raises(RetryError) as exc_info:
        await fetch_fault_label("12")

    assert isinstance(exc_info.value.last_attempt.exception(), FaultLabelAPIException)


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get")
@patch("tenacity.wait_exponential.__call__", return_value=0.01)
async def test_fetch_fault_label_unexpected_status(_, mock_get):
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_response.text.return_value = "Not Found"

    # Setup async context manager mocks
    mock_get.return_value.__aenter__.return_value = mock_response

    with pytest.raises(RetryError) as exc_info:
        await fetch_fault_label("12")

    # Assert the final raised exception is the expected one
    assert isinstance(exc_info.value.last_attempt.exception(), FaultLabelAPIException)


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get")
@patch("tenacity.wait_exponential.__call__", return_value=0.01)
async def test_fetch_fault_label_list_with_valid_label(_, mock_get):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = [{"label": "Overheat"}]

    mock_get.return_value.__aenter__.return_value = mock_response

    label = await fetch_fault_label("1")
    assert label == "Overheat"


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.get")
@patch("tenacity.wait_exponential.__call__", return_value=0.01)
async def test_fetch_fault_label_unexpected_response_type(_, mock_get):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = "unexpected string"

    mock_get.return_value.__aenter__.return_value = mock_response

    label = await fetch_fault_label("2")
    assert label == "Unknown"


@pytest.mark.asyncio
@patch("src.fastapi.rabbitmq_handlers.fault.utils.FaultEventModel")
async def test_save_fault_event_success(mock_fault_model):
    # Setup dummy Pydantic response
    response = FaultEventResponse(
        device_id="dev1",
        device_name="Device 1",
        timestamp=datetime(2025, 1, 1, 12, 0, 0),
        fault_payload="base64encoded",
        fault_code="fc1",
        fault_label="Overheat",
    )

    # Prepare mock model instance
    mock_instance = MagicMock(id=123)
    mock_fault_model.return_value = mock_instance

    db = AsyncMock()
    db.add = MagicMock()

    result = await save_fault_event(db, response)

    # Assertions
    mock_fault_model.assert_called_once_with(**response.model_dump())
    db.add.assert_called_once_with(mock_instance)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(mock_instance)
    assert result == mock_instance


@pytest.mark.asyncio
@patch("src.fastapi.rabbitmq_handlers.fault.utils.FaultEventModel")
async def test_save_fault_event_failure(mock_fault_model):
    response = FaultEventResponse(
        device_id="dev1",
        device_name="Device 1",
        timestamp=datetime(2025, 1, 1, 12, 0, 0),
        fault_payload="base64encoded",
        fault_code="fc1",
        fault_label="Overheat",
    )

    mock_instance = MagicMock()
    mock_fault_model.return_value = mock_instance

    db = AsyncMock()
    db.add = MagicMock()
    db.commit.side_effect = RuntimeError("DB commit failed")

    with pytest.raises(FaultDatabaseSaveException) as exc_info:
        await save_fault_event(db, response)

    db.rollback.assert_awaited_once()
    assert "dev1" in str(exc_info.value)
    assert "fc1" in str(exc_info.value)


@pytest.mark.asyncio
@patch("src.fastapi.rabbitmq_handlers.fault.utils.redis_manager.redis_client")
async def test_cache_fault_segment_success(mock_redis_client):
    # Arrange
    mock_redis_client.hset = AsyncMock()
    mock_redis_client.expire = AsyncMock()
    mock_redis_client.hlen = AsyncMock(return_value=5)

    device_id = "dev1"
    fault_code = "fc1"
    timestamp = datetime(2025, 1, 1, 12, 0)
    sequence = 2
    fault_bits = "010101"

    # Act
    count = await cache_fault_segment(
        device_id=device_id,
        fault_code=fault_code,
        timestamp=timestamp,
        sequence=sequence,
        fault_bits=fault_bits,
        expire_secs=1800,
    )

    # Assert
    key = f"fault_parts:{device_id}:{fault_code}:{timestamp}"
    mock_redis_client.hset.assert_awaited_once_with(key, sequence, fault_bits)
    mock_redis_client.expire.assert_awaited_once_with(key, 1800)
    mock_redis_client.hlen.assert_awaited_once_with(key)
    assert count == 5


@pytest.mark.asyncio
@patch("src.fastapi.rabbitmq_handlers.fault.utils.redis_manager.redis_client")
async def test_cache_fault_segment_failure(mock_redis_client):
    # Arrange
    mock_redis_client.hset = AsyncMock(side_effect=RuntimeError("Redis down"))
    mock_redis_client.expire = AsyncMock()
    mock_redis_client.hlen = AsyncMock()

    with pytest.raises(RuntimeError, match="Redis down"):
        await cache_fault_segment(
            device_id="dev1",
            fault_code="fc1",
            timestamp=datetime.now(),
            sequence=1,
            fault_bits="1111",
        )


@pytest.mark.asyncio
@patch("src.fastapi.rabbitmq_handlers.fault.utils.redis_manager.redis_client")
async def test_assemble_all_fault_segments_success(mock_redis_client):
    # Arrange
    mock_redis_client.hgetall = AsyncMock(
        return_value={b"0": b"01010101", b"1": b"10101010"}
    )
    mock_redis_client.delete = AsyncMock()

    device_id = "dev123"
    fault_code = "FC01"
    timestamp = datetime(2025, 1, 1, 12, 0)
    total_number = 2

    # Act
    bitstring, payload = await assemble_all_fault_segments(
        device_id=device_id,
        fault_code=fault_code,
        timestamp=timestamp,
        total_number=total_number,
    )

    # Assert
    assert bitstring == "0101010110101010"
    expected_bytes = bytes([int("01010101", 2), int("10101010", 2)])
    assert payload == expected_bytes
    mock_redis_client.hgetall.assert_awaited_once()
    mock_redis_client.delete.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.fastapi.rabbitmq_handlers.fault.utils.redis_manager.redis_client")
async def test_assemble_all_fault_segments_incomplete_data(mock_redis_client):
    # Simulate missing segment "1"
    mock_redis_client.hgetall = AsyncMock(return_value={b"0": b"01010101"})
    mock_redis_client.delete = AsyncMock()

    with pytest.raises(KeyError):
        await assemble_all_fault_segments(
            device_id="dev1",
            fault_code="FC99",
            timestamp=datetime.now(),
            total_number=2,
        )

    mock_redis_client.delete.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.fastapi.rabbitmq_handlers.fault.utils.redis_manager.redis_client")
async def test_assemble_all_fault_segments_redis_failure(mock_redis_client):
    # Simulate Redis failure
    mock_redis_client.hgetall = AsyncMock(side_effect=RuntimeError("Redis unreachable"))
    mock_redis_client.delete = AsyncMock()

    with pytest.raises(RuntimeError, match="Redis unreachable"):
        await assemble_all_fault_segments(
            device_id="dev5", fault_code="fc5", timestamp=datetime.now(), total_number=1
        )

    mock_redis_client.delete.assert_awaited_once()


def test_fault_event_model_repr():
    event = FaultEventModel(
        id=1,
        device_id="dev123",
        device_name="Sensor A",
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        fault_payload="abc123",
        fault_code="F01",
        fault_label="Overheat",
    )

    output = repr(event)

    assert "<FaultEvent(" in output
    assert "device_id='dev123'" in output
    assert "timestamp='2024-01-01 12:00:00+00:00'" in output
    assert "fault_code='F01'" in output
    assert "fault_label='Overheat'" in output
