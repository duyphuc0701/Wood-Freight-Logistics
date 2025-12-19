import base64
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.fastapi.rabbitmq_handlers.fault.exceptions import (
    FaultCacheSegmentException,
    FaultConstructPayloadException,
    FaultDatabaseSaveException,
    FaultDecodeException,
    FaultDeviceAPIException,
    FaultLabelAPIException,
    FaultSendAlertException,
)
from src.fastapi.rabbitmq_handlers.fault.handler import handle_fault_event
from src.fastapi.rabbitmq_handlers.gps.exceptions import GPSDeviceAPIException


@pytest.mark.asyncio
@patch("src.fastapi.rabbitmq_handlers.fault.handler.FaultEventCreate.from_base64")
async def test_decode_error(mock_from_base64):
    payload = "whatever"
    mock_from_base64.side_effect = FaultDecodeException(
        payload, "invalid base64 format"
    )

    # Execute
    db = AsyncMock()
    result = await handle_fault_event(db=db, payload="whatever")

    # Verify that an error is returned and includes the original payload
    assert "error" in result
    assert "whatever" in result["error"]


@pytest.mark.asyncio
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.fetch_device_name",
    new_callable=AsyncMock,
)
@patch("src.fastapi.rabbitmq_handlers.fault.handler.FaultEventCreate.from_base64")
async def test_device_name_not_found(mock_from_base64, mock_fetch_device_name):
    # Prepare dummy event
    dummy = AsyncMock(
        device_id="dev1",
        timestamp=datetime(2021, 3, 31, 9, 12),
        fault_bits="fb",
        fault_code="code",
        sequence=0,
        total_number=1,
    )
    mock_from_base64.return_value = dummy

    # Raise custom exception
    mock_fetch_device_name.side_effect = FaultDeviceAPIException(device_id="dev1")

    # Call handler
    result = await handle_fault_event(db=AsyncMock(), payload="foo")

    # Assertions
    assert "error" in result
    assert "dev1" in result["error"]
    assert "Failed to fetch device name" in result["error"]


@pytest.mark.asyncio
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.fetch_device_name",
    new_callable=AsyncMock,
)
@patch("src.fastapi.rabbitmq_handlers.fault.handler.FaultEventCreate.from_base64")
async def test_device_name_empty(mock_from_base64, mock_fetch_device_name):
    # Dummy event with valid structure
    device_id = "empty"
    dummy_event = AsyncMock(
        device_id=device_id,
        timestamp=datetime(2025, 5, 1, 10, 0),
        fault_bits="fb",
        fault_code="1000",
        sequence=1,
        total_number=1,
    )
    mock_from_base64.return_value = dummy_event

    # simulate a missing device name
    mock_fetch_device_name.return_value = None

    result = await handle_fault_event(db=AsyncMock(), payload="ignored")

    # Assertions
    assert "error" in result
    assert device_id in result["error"]
    assert str(GPSDeviceAPIException(device_id)) == result["error"]


@pytest.mark.asyncio
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.cache_fault_segment",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.fetch_device_name",
    new_callable=AsyncMock,
)
@patch("src.fastapi.rabbitmq_handlers.fault.handler.FaultEventCreate.from_base64")
async def test_cache_fault_segment_error(
    mock_from_base64, mock_fetch_device_name, mock_cache_fault_segment
):
    dummy = AsyncMock(
        device_id="dev",
        timestamp=datetime(2023, 1, 1, 12, 0),
        fault_bits="fb",
        fault_code="fc",
        sequence=0,
        total_number=1,
    )
    mock_from_base64.return_value = dummy
    mock_fetch_device_name.return_value = "name"
    mock_cache_fault_segment.side_effect = FaultCacheSegmentException("dev", "fc")

    # Execute
    result = await handle_fault_event(db=AsyncMock(), payload="foo")

    # Assertions
    assert "error" in result
    assert "dev" in result["error"]
    assert "fc" in result["error"]


@pytest.mark.asyncio
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.cache_fault_segment",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.fetch_device_name",
    new_callable=AsyncMock,
)
@patch("src.fastapi.rabbitmq_handlers.fault.handler.FaultEventCreate.from_base64")
async def test_pending_segments(
    mock_from_base64, mock_fetch_device_name, mock_cache_fault_segment
):
    # Prepare a dummy FaultEventCreate instance
    dummy = AsyncMock(
        device_id="dev",
        timestamp=datetime(2023, 1, 1, 12, 0),
        fault_bits="fb",
        fault_code="fc",
        sequence=0,
        total_number=3,
    )
    mock_from_base64.return_value = dummy
    mock_fetch_device_name.return_value = "name"
    mock_cache_fault_segment.return_value = 1

    # Call handler
    result = await handle_fault_event(db=AsyncMock(), payload="foo")

    # Validate response
    assert result["status"] == "pending"
    assert result["received"] == 1
    assert result["total"] == 3


@pytest.mark.asyncio
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.assemble_all_fault_segments",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.cache_fault_segment",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.fetch_device_name",
    new_callable=AsyncMock,
)
@patch("src.fastapi.rabbitmq_handlers.fault.handler.FaultEventCreate.from_base64")
async def test_construct_fault_payload_error(
    mock_from_base64,
    mock_fetch_device_name,
    mock_cache_fault_segment,
    mock_assemble_all,
):
    # Dummy fault event
    dummy = AsyncMock(
        device_id="dev",
        timestamp=datetime(2023, 1, 1, 12, 0),
        fault_bits="fb",
        fault_code="fc",
        sequence=0,
        total_number=1,
    )
    mock_from_base64.return_value = dummy
    mock_fetch_device_name.return_value = "name"
    mock_cache_fault_segment.return_value = 1  # all parts received
    mock_assemble_all.side_effect = FaultConstructPayloadException("dev", "fc")

    # Execute
    result = await handle_fault_event(db=AsyncMock(), payload="foo")

    # Assertions
    assert "error" in result
    assert "dev" in result["error"]
    assert "fc" in result["error"]


@pytest.mark.asyncio
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.fetch_fault_label",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.assemble_all_fault_segments",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.cache_fault_segment",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.fetch_device_name",
    new_callable=AsyncMock,
)
@patch("src.fastapi.rabbitmq_handlers.fault.handler.FaultEventCreate.from_base64")
async def test_fetch_fault_label_error(
    mock_from_base64,
    mock_fetch_device_name,
    mock_cache_fault_segment,
    mock_assemble_all_fault_segments,
    mock_fetch_fault_label,
):
    # Setup dummy FaultEventCreate object
    dummy = AsyncMock(
        device_id="dev",
        timestamp=datetime(2023, 1, 1, 12, 0),
        fault_bits="fb",
        fault_code="fc",
        sequence=0,
        total_number=1,
    )
    mock_from_base64.return_value = dummy
    mock_fetch_device_name.return_value = "name"
    mock_cache_fault_segment.return_value = 1
    mock_assemble_all_fault_segments.return_value = ("PL", b"bytes")
    mock_fetch_fault_label.side_effect = FaultLabelAPIException("fc")

    # Call handler
    result = await handle_fault_event(db=AsyncMock(), payload="foo")

    # Assert the error response
    assert "error" in result
    assert "fc" in result["error"]


@pytest.mark.asyncio
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.save_fault_event",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.fetch_fault_label",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.assemble_all_fault_segments",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.cache_fault_segment",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.fetch_device_name",
    new_callable=AsyncMock,
)
@patch("src.fastapi.rabbitmq_handlers.fault.handler.FaultEventCreate.from_base64")
async def test_save_fault_error(
    mock_from_base64,
    mock_fetch_device_name,
    mock_cache_fault_segment,
    mock_assemble_all_fault_segments,
    mock_fetch_fault_label,
    mock_save_fault_event,
):
    # Create dummy fault event
    dummy = AsyncMock(
        device_id="dev",
        timestamp=datetime(2023, 1, 1, 12, 0),
        fault_bits="fb",
        fault_code="fc",
        sequence=0,
        total_number=1,
    )
    mock_from_base64.return_value = dummy
    mock_fetch_device_name.return_value = "name"
    mock_cache_fault_segment.return_value = 1
    mock_assemble_all_fault_segments.return_value = ("PL", b"bytes")
    mock_fetch_fault_label.return_value = "LBL"
    mock_save_fault_event.side_effect = FaultDatabaseSaveException("dev", "fc")

    # Run the handler
    result = await handle_fault_event(db=AsyncMock(), payload="foo")

    # Validate error
    assert "error" in result
    assert "dev" in result["error"]
    assert "fc" in result["error"]
    assert "Failed to save fault event to database" in result["error"]


@pytest.mark.asyncio
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.send_alert_event",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.save_fault_event",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.fetch_fault_label",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.assemble_all_fault_segments",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.cache_fault_segment",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.fetch_device_name",
    new_callable=AsyncMock,
)
@patch("src.fastapi.rabbitmq_handlers.fault.handler.FaultEventCreate.from_base64")
async def test_send_alert_error(
    mock_from_base64,
    mock_fetch_device_name,
    mock_cache_fault_segment,
    mock_assemble_all_fault_segments,
    mock_fetch_fault_label,
    mock_save_fault_event,
    mock_send_alert_event,
):
    # Dummy event
    dummy = AsyncMock(
        device_id="dev",
        timestamp=datetime(2023, 1, 1, 12, 0),
        fault_bits="fb",
        fault_code="fc",
        sequence=0,
        total_number=1,
    )
    mock_from_base64.return_value = dummy
    mock_fetch_device_name.return_value = "name"
    mock_cache_fault_segment.return_value = 1
    mock_assemble_all_fault_segments.return_value = ("PL", b"bytes")
    mock_fetch_fault_label.return_value = "LBL"
    mock_save_fault_event.return_value = None
    mock_send_alert_event.side_effect = FaultSendAlertException("fc")

    # Run handler
    result = await handle_fault_event(db=AsyncMock(), payload="foo")

    # Ensure alert failure didn't break the flow
    assert "error" in result
    assert "fc" in result["error"]

    # Ensure alert was attempted
    mock_send_alert_event.assert_awaited_once()


@pytest.mark.asyncio
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.send_alert_event",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.save_fault_event",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.fetch_fault_label",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.assemble_all_fault_segments",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.cache_fault_segment",
    new_callable=AsyncMock,
)
@patch(
    "src.fastapi.rabbitmq_handlers.fault.handler.fetch_device_name",
    new_callable=AsyncMock,
)
@patch("src.fastapi.rabbitmq_handlers.fault.handler.FaultEventCreate.from_base64")
async def test_full_success(
    mock_from_base64,
    mock_fetch_device_name,
    mock_cache_fault_segment,
    mock_assemble_all_fault_segments,
    mock_fetch_fault_label,
    mock_save_fault_event,
    mock_send_alert_event,
):
    # Setup dummy event
    dummy = AsyncMock(
        device_id="devX",
        timestamp=datetime(2023, 5, 9, 12, 0),
        fault_bits="fbX",
        fault_code="fcX",
        sequence=0,
        total_number=1,
    )
    mock_from_base64.return_value = dummy
    mock_fetch_device_name.return_value = "device-name"
    mock_cache_fault_segment.return_value = 1
    mock_assemble_all_fault_segments.return_value = ("RAW_PAYLOAD", b"\x00\x01")
    mock_fetch_fault_label.return_value = "LABEL_X"

    # Run handler
    db = AsyncMock()
    result = await handle_fault_event(db=db, payload="unused")

    # Validate final result
    assert result["device_id"] == "devX"
    assert result["device_name"] == "device-name"
    assert result["timestamp"] == datetime(2023, 5, 9, 12, 0)
    assert result["fault_payload"] == base64.b64encode(b"\x00\x01").decode("ascii")
    assert result["fault_label"] == "LABEL_X"

    # Confirm DB save and WebSocket alert were both invoked
    mock_save_fault_event.assert_awaited_once()
    mock_send_alert_event.assert_awaited_once()
