import asyncio
import inspect
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from fastapi import FastAPI
from src.fastapi.database.database import DatabaseManager
from src.fastapi.main import (
    app,
    consume_queue,
    custom_openapi,
    ingest_event,
    init_db,
    lifespan,
)
from tests.conftest import async_client  # noqa: F401

pytestmark = pytest.mark.asyncio(loop_scope="module")


@patch("sqlalchemy.ext.asyncio.engine.AsyncEngine.begin")
async def test_init_db_runs(mock_engine):
    mock_engine.return_value = AsyncMock()
    await init_db()


async def test_custom_openapi():
    custom_openapi()
    pass


async def test_custom_openapi_cached():
    from src.fastapi.main import app

    # Mock the OpenAPI schema to simulate a cached version
    app.openapi_schema = {"dummy": True}

    from src.fastapi.main import custom_openapi

    schema = custom_openapi()
    assert schema == {"dummy": True}


@patch("src.fastapi.main.handle_gps_event", new_callable=AsyncMock)
@patch("src.fastapi.main.db")
async def test_consume_gps_queue(mock_db, mock_handle_gps_event):
    DatabaseManager.is_connected = True

    mock_session = AsyncMock()
    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session
    mock_session_cm.__aexit__.return_value = None

    fut = asyncio.Future()
    fut.set_result(mock_session_cm)
    mock_db.get_client.return_value = fut

    message = MagicMock()
    message.body = b'{"lat": 10, "lng": 20}'

    proc_ctx = AsyncMock()
    proc_ctx.__aenter__.return_value = None
    proc_ctx.__aexit__.return_value = None
    message.process = MagicMock(return_value=proc_ctx)

    message_iter = AsyncMock()
    message_iter.__aiter__.return_value = [message]

    queue_ctx = AsyncMock()
    queue_ctx.__aenter__.return_value = message_iter
    queue_ctx.__aexit__.return_value = None

    queue_mock = AsyncMock()
    queue_mock.iterator = MagicMock(return_value=queue_ctx)

    channel = AsyncMock()
    channel.declare_queue.return_value = queue_mock

    await consume_queue(channel, "gps_queue")

    mock_handle_gps_event.assert_awaited_once_with(
        mock_session, '{"lat": 10, "lng": 20}'
    )


@patch("src.fastapi.main.handle_fault_event", new_callable=AsyncMock)
@patch("src.fastapi.main.db")
async def test_consume_fault_queue(mock_db, mock_handle_fault_event):
    DatabaseManager.is_connected = True

    mock_session = AsyncMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_session
    mock_cm.__aexit__.return_value = None
    fut = asyncio.Future()
    fut.set_result(mock_cm)
    mock_db.get_client.return_value = fut

    message = MagicMock()
    message.body = b'{"error": "fault"}'
    proc_ctx = AsyncMock()
    proc_ctx.__aenter__.return_value = None
    proc_ctx.__aexit__.return_value = None
    message.process = MagicMock(return_value=proc_ctx)

    msg_iter = AsyncMock()
    msg_iter.__aiter__.return_value = [message]

    queue_ctx = AsyncMock()
    queue_ctx.__aenter__.return_value = msg_iter
    queue_ctx.__aexit__.return_value = None

    queue_mock = AsyncMock()
    queue_mock.iterator = MagicMock(return_value=queue_ctx)

    channel = AsyncMock()
    channel.declare_queue.return_value = queue_mock

    await consume_queue(channel, "fault_queue")

    mock_handle_fault_event.assert_awaited_once_with(mock_session, '{"error": "fault"}')


@patch("src.fastapi.main.db")
async def test_consume_unknown_queue(mock_db, caplog):
    DatabaseManager.is_connected = True

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = AsyncMock()
    mock_cm.__aexit__.return_value = None
    fut = asyncio.Future()
    fut.set_result(mock_cm)
    mock_db.get_client.return_value = fut

    message = MagicMock()
    message.body = b'{"foo": "bar"}'
    proc_ctx = AsyncMock()
    proc_ctx.__aenter__.return_value = None
    proc_ctx.__aexit__.return_value = None
    message.process = MagicMock(return_value=proc_ctx)

    msg_iter = AsyncMock()
    msg_iter.__aiter__.return_value = [message]
    queue_ctx = AsyncMock()
    queue_ctx.__aenter__.return_value = msg_iter
    queue_ctx.__aexit__.return_value = None

    queue_mock = AsyncMock()
    queue_mock.iterator = MagicMock(return_value=queue_ctx)

    channel = AsyncMock()
    channel.declare_queue.return_value = queue_mock

    with caplog.at_level("WARNING"):
        await consume_queue(channel, "some_unknown_queue")

    assert "Unknown queue" in caplog.text


@patch("src.fastapi.main.db")
async def test_consume_queue_error(mock_db, caplog):
    DatabaseManager.is_connected = True

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = AsyncMock()
    mock_cm.__aexit__.return_value = None
    fut = asyncio.Future()
    fut.set_result(mock_cm)
    mock_db.get_client.return_value = fut

    message = MagicMock()

    class BadBytes(bytes):
        def decode(self, *args, **kwargs):
            raise ValueError("bad decode")

    message.body = BadBytes(b"\xff")
    proc_ctx = AsyncMock()
    proc_ctx.__aenter__.return_value = None
    proc_ctx.__aexit__.return_value = None
    message.process = MagicMock(return_value=proc_ctx)

    msg_iter = AsyncMock()
    msg_iter.__aiter__.return_value = [message]
    queue_ctx = AsyncMock()
    queue_ctx.__aenter__.return_value = msg_iter
    queue_ctx.__aexit__.return_value = None

    queue_mock = AsyncMock()
    queue_mock.iterator = MagicMock(return_value=queue_ctx)

    channel = AsyncMock()
    channel.declare_queue.return_value = queue_mock

    with caplog.at_level("ERROR"):
        await consume_queue(channel, "gps_queue")

    assert "Failed to process message" in caplog.text


@patch("src.fastapi.main.asyncio.gather", new_callable=AsyncMock)
@patch("src.fastapi.main.asyncio.create_task")
@patch("src.fastapi.main.consume_queue", new_callable=AsyncMock)
@patch("src.fastapi.main.aio_pika.connect_robust", new_callable=AsyncMock)
async def test_ingest_event(
    mock_connect_robust,
    mock_consume_queue,
    mock_create_task,
    mock_gather,
):
    mock_conn = AsyncMock()
    mock_connect_robust.return_value = mock_conn
    mock_channel = AsyncMock()
    mock_conn.channel.return_value = mock_channel
    mock_exchange = AsyncMock()
    mock_channel.declare_exchange.return_value = mock_exchange

    mock_gps_queue = AsyncMock()
    mock_fault_queue = AsyncMock()
    mock_channel.declare_queue.side_effect = [mock_gps_queue, mock_fault_queue]

    mock_gps_queue.bind = AsyncMock()
    mock_fault_queue.bind = AsyncMock()

    task1, task2 = object(), object()
    mock_create_task.side_effect = [task1, task2]

    await ingest_event()

    mock_consume_queue.assert_any_call(mock_channel, "gps_queue")
    mock_consume_queue.assert_any_call(mock_channel, "fault_queue")
    assert mock_consume_queue.call_count == 2

    assert mock_create_task.call_count == 2
    for args, _ in mock_create_task.call_args_list:
        coro = args[0]
        assert inspect.iscoroutine(coro)

    mock_gather.assert_awaited_once()
    g_args, g_kwargs = mock_gather.await_args
    assert g_args == (task1, task2)
    assert g_kwargs == {}


async def test_sqlalchemy_exception_handler(async_client):  # noqa: F811
    """Test SQLAlchemy exception handler returns 503."""
    response = await async_client.get("/force-sqlalchemy-error")
    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert "Database connection error" in response.json()["detail"]


async def test_custom_openapi_has_api_key_security(async_client):  # noqa: F811
    """Test custom OpenAPI includes APIKeyHeader."""
    schema = custom_openapi()
    assert "components" in schema
    assert "securitySchemes" in schema["components"]
    assert "APIKeyHeader" in schema["components"]["securitySchemes"]
    security = schema["components"]["securitySchemes"]["APIKeyHeader"]
    assert security["type"] == "apiKey"
    assert security["in"] == "header"


@patch("src.fastapi.main.ingest_event", new_callable=AsyncMock)
@patch("src.fastapi.main.redis_manager.init_redis", new_callable=AsyncMock)
@patch("src.fastapi.main.redis_manager.close_redis", new_callable=AsyncMock)
@patch("src.fastapi.main.DatabaseManager.connect", new_callable=AsyncMock)
@patch("src.fastapi.main.DatabaseManager.disconnect", new_callable=AsyncMock)
@patch("src.fastapi.main.init_db", new_callable=AsyncMock)
async def test_lifespan_startup_teardown(
    mock_init_db,
    mock_disconnect,
    mock_connect,
    mock_close_redis,
    mock_init_redis,
    mock_ingest_event,
):
    app = FastAPI(lifespan=lifespan)

    async with app.router.lifespan_context(app):
        mock_connect.assert_awaited_once()
        mock_init_db.assert_awaited_once()
        mock_init_redis.assert_awaited_once()

    # teardown
    mock_close_redis.assert_awaited_once()
    mock_disconnect.assert_awaited_once()


# Optional route for testing exception handler (not in original main.py)
@app.get("/force-sqlalchemy-error")
async def force_sqlalchemy_error():
    raise SQLAlchemyError("Simulated DB error")
