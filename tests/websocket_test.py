from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.fastapi.websocket.client import send_alert_event
from src.fastapi.websocket.models import AlertEvent


async def test_send_alert_event_success():
    mock_ws = AsyncMock()
    mock_ws.recv.return_value = "ack"
    mock_connect = MagicMock()
    mock_connect.return_value.__aenter__.return_value = mock_ws

    with patch("src.fastapi.websocket.client.websockets.connect", mock_connect):
        alert_event = AlertEvent(
            device_id="device123",
            device_name="sensor-01",
            event_type="overheat",
            timestamp=datetime(2025, 5, 7, 12, 0, 0),
            data={"cpu": 90},
        )
        response = await send_alert_event(alert_event)

    mock_ws.send.assert_awaited_once()
    mock_ws.recv.assert_awaited_once()
    assert response == "ack"


async def test_send_alert_event_failure():
    mock_connect = MagicMock(side_effect=Exception("fail"))
    with patch("src.fastapi.websocket.client.websockets.connect", mock_connect):
        alert = AlertEvent(
            device_id="device123",
            device_name="sensor-01",
            event_type="overheat",
            timestamp=datetime(2025, 5, 7, 12, 0, 0),
            data={"cpu": 90},
        )
        with pytest.raises(Exception):
            await send_alert_event.__wrapped__(alert)
