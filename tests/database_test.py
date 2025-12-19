from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from fastapi import HTTPException, status
from src.fastapi.database.database import DatabaseManager
from src.fastapi.database.dependencies import verify_database

pytestmark = pytest.mark.asyncio(loop_scope="module")


# Test connect method
@patch("src.fastapi.database.database.engine")
async def test_connect_success(mock_connect):
    mock_connect.return_value = AsyncMock()
    await DatabaseManager.connect()
    assert DatabaseManager.is_connected is True


@patch("sqlalchemy.ext.asyncio.engine.AsyncEngine.connect")
async def test_connect_failure(mock_connect):
    DatabaseManager.is_connected = False
    mock_connect.side_effect = SQLAlchemyError("Connection error")
    with pytest.raises(SQLAlchemyError):
        await DatabaseManager.connect()
    assert DatabaseManager.is_connected is False


@patch("sqlalchemy.ext.asyncio.engine.AsyncEngine.connect")
async def test_connect_already_connected(mock_connect, caplog):
    mock_connect.return_value = AsyncMock()
    DatabaseManager.is_connected = True
    with caplog.at_level("INFO"):
        await DatabaseManager.connect()
        assert DatabaseManager.is_connected is True
        assert "Already connected to the database" in caplog.text


async def test_disconnect_success():
    DatabaseManager.is_connected = True
    await DatabaseManager.disconnect()
    assert DatabaseManager.is_connected is False


@patch("sqlalchemy.ext.asyncio.engine.AsyncEngine.dispose")
async def test_disconnect_failure(mock_dispose):
    DatabaseManager.is_connected = True
    mock_dispose.side_effect = SQLAlchemyError("Disconnection error")
    with pytest.raises(SQLAlchemyError):
        await DatabaseManager.disconnect()
    assert DatabaseManager.is_connected is True


@patch("src.fastapi.database.database.engine")
async def test_reconnect_success(mock_engine):
    DatabaseManager.is_connected = False
    mock_engine.connect.return_value = AsyncMock()
    await DatabaseManager.reconnect()
    assert DatabaseManager.is_connected is True


@patch("sqlalchemy.ext.asyncio.engine.AsyncEngine.connect")
async def test_reconnect_failure(mock_connect):
    from src.fastapi.database.database import DatabaseManager

    DatabaseManager.is_connected = False
    with patch.object(DatabaseManager, "retry_interval", 0):
        mock_connect.side_effect = SQLAlchemyError("Reconnection error")
        with pytest.raises(SQLAlchemyError):
            await DatabaseManager.reconnect(max_attempts=1)


@patch("src.fastapi.database.database.SessionLocal")
async def test_get_client_success(mock_session):
    mock_session.return_value = AsyncMock()
    DatabaseManager.is_connected = True
    session = await DatabaseManager.get_client()
    assert isinstance(session, AsyncMock)


async def test_get_client_failure():
    DatabaseManager.is_connected = False
    with pytest.raises(RuntimeError):
        await DatabaseManager.get_client()


@patch("src.fastapi.database.database.engine")
async def test_list_tables_success(mock_engine):
    mock_engine.connect.return_value = AsyncMock()
    tables = await DatabaseManager.list_tables()
    assert tables == []


@patch("src.fastapi.database.database.engine")
async def test_list_tables_failure(mock_engine):
    mock_engine.connect.side_effect = SQLAlchemyError("Connection error")
    with pytest.raises(SQLAlchemyError):
        await DatabaseManager.list_tables()


@patch("src.fastapi.database.dependencies.db.get_client")
async def test_verify_database_connected(mock_get_client):
    mock_get_client.return_value = AsyncMock()
    DatabaseManager.is_connected = True
    session = await verify_database()
    assert isinstance(session, AsyncMock)


@patch("src.fastapi.database.dependencies.db.get_client")
@patch("src.fastapi.database.dependencies.db.reconnect")
async def test_verify_database_reconnect_success(mock_reconnect, mock_get_client):
    DatabaseManager.is_connected = False
    mock_reconnect.return_value = AsyncMock()
    mock_get_client.return_value = AsyncMock()
    session = await verify_database()
    assert isinstance(session, AsyncMock)


@patch("src.fastapi.database.dependencies.db.reconnect")
async def test_verify_database_reconnect_failure(mock_reconnect):
    DatabaseManager.is_connected = False
    mock_reconnect.side_effect = SQLAlchemyError("Reconnection error")
    with pytest.raises(HTTPException) as exc_info:
        await verify_database()
    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
