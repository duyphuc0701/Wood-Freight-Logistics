import asyncio
import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.alert.rules import RULES
from src.alert.schemas import AlertEvent
from src.alert.utils import check_suppression_period, process_alert


@pytest.mark.asyncio
@patch("src.alert.utils.redis_manager.redis_client")
async def test_suppressed_event_returns_true(mock_redis_client):
    mock_redis_client.get = AsyncMock(return_value=b"suppressed")
    mock_redis_client.setex = AsyncMock()

    # 2 bytes = 5 seconds
    payload = b"0000000000000005"
    result = await check_suppression_period("fc1", payload)

    mock_redis_client.get.assert_awaited_once()
    mock_redis_client.setex.assert_not_called()
    assert result is True


@pytest.mark.asyncio
@patch("src.alert.utils.redis_manager.redis_client")
async def test_new_event_sets_suppression_and_returns_false(mock_redis_client):
    mock_redis_client.get = AsyncMock(return_value=None)
    mock_redis_client.setex = AsyncMock()

    payload = b"abcde" + (5).to_bytes(2, "big")
    result = await check_suppression_period("fc1", payload)

    mock_redis_client.get.assert_awaited_once()
    mock_redis_client.setex.assert_awaited_once_with("suppression:fc1", 5, "suppressed")
    assert result is False


@pytest.mark.asyncio
@patch("src.alert.utils.redis_manager.redis_client", None)
async def test_redis_client_none_returns_false():
    payload = b"abcde" + (10).to_bytes(2, "big")
    result = await check_suppression_period("fc1", payload)
    assert result is False


@pytest.mark.asyncio
@patch("src.alert.utils.redis_manager.redis_client")
async def test_redis_raises_exception_logs_and_returns_false(mock_redis_client, caplog):
    mock_redis_client.get = AsyncMock(side_effect=RuntimeError("Redis error"))

    payload = b"abcde" + (15).to_bytes(2, "big")
    with caplog.at_level("ERROR"):
        result = await check_suppression_period("fc1", payload)

    assert "Suppression check error" in caplog.text
    assert "Redis error" in caplog.text
    assert result is False


@pytest.mark.asyncio
@patch("src.alert.utils.send_email", new_callable=AsyncMock)
@patch("src.alert.utils.check_suppression_period", new_callable=AsyncMock)
async def test_fault_event_suppressed(check_mock, send_mock):
    check_mock.return_value = True

    payload = base64.b64encode(b"xxxx" + (10).to_bytes(2, "big")).decode()
    event = AlertEvent(
        event_type="fault",
        device_id="dev1",
        device_name="Device 1",
        timestamp="2024-01-01T00:00:00",
        data={
            "fault_code": "1",
            "fault_payload": payload,
        },
    )

    await process_alert(event)
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
@patch(
    "src.alert.utils.check_suppression_period", side_effect=Exception("db unavailable")
)
@patch("src.alert.utils.logger")
async def test_process_alert_suppression_exception(mock_logger, mock_check):
    # Simulate a valid base64-encoded payload
    fake_payload = b"fault-payload"
    b64_payload = base64.b64encode(fake_payload).decode()

    event = AlertEvent(
        event_type="fault",
        device_id="dev123",
        device_name="Name",
        timestamp="123456",
        data={"fault_code": "F42", "fault_payload": b64_payload},
    )

    await process_alert(event)

    # Ensure suppression exception was caught and logged
    mock_check.assert_awaited_once()
    mock_logger.warning.assert_any_call("Suppression check failed: db unavailable")


@pytest.mark.asyncio
@patch("src.alert.utils.send_email", new_callable=AsyncMock)
@patch("src.alert.utils.check_suppression_period", new_callable=AsyncMock)
@patch("src.alert.utils.matches_rule", return_value=True)
@patch(
    "src.alert.utils.RULES",
    [
        MagicMock(
            email="test@example.com",
            event_types=["fault"],
            thresholds={"fault_code": ["1"]},
        )
    ],
)
async def test_fault_event_triggers_email_skipping_assert(_, check_mock, send_mock):
    check_mock.return_value = False

    payload = base64.b64encode(b"abcd" + (5).to_bytes(2, "big")).decode()
    event = AlertEvent(
        event_type="fault",
        device_id="dev123",
        device_name="Device",
        timestamp="2024-01-01T00:00:00",
        data={
            "fault_code": "1",
            "fault_payload": payload,
        },
    )

    await process_alert(event)

    args, _ = send_mock.call_args
    assert "test@example.com" in args


@pytest.mark.asyncio
@patch("src.alert.utils.send_email", new_callable=AsyncMock)
@patch("src.alert.utils.check_suppression_period", new_callable=AsyncMock)
@patch("src.alert.utils.matches_rule", return_value=False)
@patch(
    "src.alert.utils.RULES",
    [
        MagicMock(
            email="test@example.com", event_types=["gps"], thresholds={"speed": 60}
        )
    ],
)
async def test_no_matching_rules_sends_nothing(_, check_mock, send_mock):
    check_mock.return_value = False

    event = AlertEvent(
        event_type="gps",
        device_id="dev123",
        device_name="GPS Device",
        timestamp="2024-01-01T00:00:00",
        data={"speed": 30},
    )

    await process_alert(event)

    send_mock.assert_not_awaited()


@pytest.mark.asyncio
@patch("src.alert.utils.send_email", new_callable=AsyncMock)
@patch("src.alert.utils.check_suppression_period", new_callable=AsyncMock)
@patch("src.alert.utils.matches_rule", return_value=True)
@patch(
    "src.alert.utils.RULES",
    [
        MagicMock(
            email="test@example.com", event_types=["gps"], thresholds={"speed": 60}
        )
    ],
)
async def test_multiple_matching_thresholds(_, check_mock, send_mock):
    check_mock.return_value = False

    event = AlertEvent(
        event_type="gps",
        device_id="dev123",
        device_name="GPS Device",
        timestamp="2024-01-01T00:00:00",
        data={"speed": 70},
    )

    await process_alert(event)

    await asyncio.sleep(0)

    send_mock.assert_awaited_once()

    args, _ = send_mock.call_args
    subject = args[1]
    assert "speed=70" in subject


@pytest.mark.asyncio
@patch("src.alert.utils.matches_rule", return_value=True)
@patch("src.alert.utils.send_email", new_callable=AsyncMock)
@patch("src.alert.utils.logger")
async def test_process_alert_threshold_key_missing(
    mock_logger, mock_send_email, mock_matches_rule
):
    rule = MagicMock()
    rule.email = "ops@example.com"
    rule.thresholds = {"temperature": 75}

    RULES.clear()
    RULES.append(rule)

    event = AlertEvent(
        event_type="status",
        device_id="dev321",
        device_name="Name",
        timestamp="123456",
        data={"humidity": 50},
    )

    await process_alert(event)

    await asyncio.sleep(0)

    mock_send_email.assert_awaited_once()
    args, kwargs = mock_send_email.call_args
    assert "no matching thresholds" in args[1]


@pytest.mark.asyncio
@patch("src.alert.utils.asyncio.create_task", side_effect=Exception("Task crash"))
@patch("src.alert.utils.matches_rule", return_value=True)
@patch("src.alert.utils.logger")
async def test_process_alert_notification_failure(
    mock_logger, mock_matches_rule, mock_create_task
):
    # Setup a rule with a numeric threshold
    rule = MagicMock()
    rule.email = "alerts@example.com"
    rule.thresholds = {"speed": 70.0}

    RULES.clear()
    RULES.append(rule)

    event = AlertEvent(
        event_type="gps",
        device_id="device12",
        device_name="Name",
        timestamp="123456",
        data={"speed": 80.0},
    )

    await process_alert(event)

    await asyncio.sleep(0)

    mock_create_task.assert_called_once()
    mock_logger.error.assert_any_call(
        f"Failed to schedule notification for {rule.email}: Task crash"
    )
