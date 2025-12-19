import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from websockets.http11 import Request, Response

from src.alert.main import (
    alerts_handler,
    main,
    process_request,
    run_app,
    start_alert_server,
)


def test_process_request_health():
    req = Request(path="/health", headers=Headers())
    result = process_request(None, req)

    assert isinstance(result, Response)
    assert result.status_code == 200
    assert result.reason_phrase == "OK"
    assert result.body == b"OK"


def test_process_request_other():
    req = Request(path="/other", headers=Headers())
    result = process_request(None, req)

    assert result is None


@pytest.mark.asyncio
@patch("src.alert.main.process_alert")
@patch("src.alert.main.AlertEvent.model_validate_json")
async def test_alerts_handler_valid_message(mock_validate_json, mock_process_alert):
    mock_websocket = AsyncMock()
    mock_event = MagicMock(event_type="type1", device_id="dev1")

    mock_validate_json.return_value = mock_event
    mock_websocket.__aiter__.return_value = ["valid_message"]

    await alerts_handler(mock_websocket)

    mock_validate_json.assert_called_once_with("valid_message")
    mock_process_alert.assert_called_once_with(mock_event)
    mock_websocket.send.assert_called_with(
        json.dumps({"status": "received", "event_type": "type1", "device_id": "dev1"})
    )


@pytest.mark.asyncio
@patch("src.alert.main.AlertEvent.model_validate_json")
async def test_alerts_handler_invalid_payload(mock_validate_json):
    mock_websocket = AsyncMock()
    mock_websocket.__aiter__.return_value = ["bad_message"]

    mock_validate_json.side_effect = ValueError("bad data")

    await alerts_handler(mock_websocket)

    mock_websocket.send.assert_called_with(
        json.dumps({"status": "error", "reason": "bad data"})
    )


@pytest.mark.asyncio
@patch("src.alert.main.process_alert", side_effect=Exception("unexpected crash"))
@patch("src.alert.main.AlertEvent.model_validate_json")
async def test_alerts_handler_process_exception(mock_validate_json, mock_process_alert):
    mock_websocket = AsyncMock()
    mock_event = MagicMock(event_type="eventY", device_id="devY")

    mock_websocket.__aiter__.return_value = ["messageY"]
    mock_validate_json.return_value = mock_event

    await alerts_handler(mock_websocket)

    mock_websocket.send.assert_called_with(
        json.dumps({"status": "received", "event_type": "eventY", "device_id": "devY"})
    )


@pytest.mark.asyncio
@patch("src.alert.main.AlertEvent.model_validate_json")
async def test_alerts_handler_connection_closed_ok(mock_validate_json):
    mock_websocket = AsyncMock()

    mock_websocket.__aiter__.side_effect = ConnectionClosedOK(None, None)

    await alerts_handler(mock_websocket)


@pytest.mark.asyncio
@patch("src.alert.main.AlertEvent.model_validate_json")
async def test_alerts_handler_connection_closed_error(mock_validate_json):
    mock_websocket = AsyncMock()

    mock_websocket.__aiter__.side_effect = ConnectionClosedError(None, None)

    await alerts_handler(mock_websocket)


@pytest.mark.asyncio
@patch("src.alert.main.AlertEvent.model_validate_json")
async def test_alerts_handler_unexpected_exception(mock_validate_json):
    mock_websocket = AsyncMock()

    mock_websocket.__aiter__.side_effect = RuntimeError("unexpected")

    await alerts_handler(mock_websocket)

    mock_websocket.send.assert_not_called()


@patch("src.alert.main.redis_manager.init_redis", new_callable=AsyncMock)
@patch("src.alert.main.redis_manager.close_redis", new_callable=AsyncMock)
@patch("src.alert.main.serve")
@patch("src.alert.main.logger")
@pytest.mark.asyncio
async def test_start_alert_server_lifecycle(
    mock_logger,
    mock_serve,
    mock_close_redis,
    mock_init_redis,
):
    serve_context = AsyncMock()
    serve_context.__aenter__.return_value = AsyncMock()
    serve_context.__aexit__.return_value = AsyncMock()
    mock_serve.return_value = serve_context

    shutdown = asyncio.Future()
    shutdown.set_result(None)

    await start_alert_server("localhost", 1234, shutdown)

    mock_init_redis.assert_awaited_once()
    mock_close_redis.assert_awaited_once()
    mock_logger.info.assert_any_call("Redis initialized; alerting service started.")
    mock_logger.info.assert_any_call("Alerting service stopped.")
    mock_serve.assert_called_once()


@pytest.mark.asyncio
@patch("src.alert.main.start_alert_server", new_callable=AsyncMock)
@patch("src.alert.main.settings")
@patch("src.alert.main.asyncio.Future")
@patch("src.alert.main.asyncio.get_running_loop")
async def test_main_function(
    mock_get_running_loop, mock_future_cls, mock_settings, mock_start_server
):
    # Prepare mocks
    mock_loop = MagicMock()
    mock_get_running_loop.return_value = mock_loop

    future = asyncio.Future()
    future.set_result(None)  # Immediately resolves
    mock_future_cls.return_value = future

    mock_settings.ALERTING_PORT = 9001

    # Run main
    await main()

    # Ensure shutdown future and signal handlers set
    mock_get_running_loop.assert_called_once()
    assert mock_loop.add_signal_handler.call_count == 2

    # Ensure server is started with correct parameters
    mock_start_server.assert_awaited_once_with("0.0.0.0", 9001, future)


@patch("src.alert.main.asyncio.run")
def test_run_app_calls_asyncio_run(mock_run):
    run_app()
    mock_run.assert_called_once()
