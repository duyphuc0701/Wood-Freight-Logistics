from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from fastapi import status
from src.fastapi.database.database import DatabaseManager
from src.fastapi.gps_devices.exceptions import (
    GPSDeviceNotFoundException,
    GPSNotFoundException,
    GPSStatsException,
)
from src.fastapi.gps_devices.schemas import GPSStatsResponse
from src.fastapi.gps_devices.utils import calculate_vehicle_stats
from tests.conftest import async_client  # noqa: F401
from tests.mocks.config_mocks import VALID_SETTINGS_DATA


@patch("src.fastapi.gps_devices.routes.db.get_client")
@patch(
    "src.fastapi.gps_devices.routes.gps_stats_service.calculate_stats",
    new_callable=AsyncMock,
)
async def test_get_stats_success(mock_calc, mock_get_client, async_client: AsyncClient):
    # Fake data
    fake = GPSStatsResponse(
        device_id="dev1",
        date="2025-05-06T00:00:00",
        total_distance_km=100,
        total_distance_miles=62.1371,
        average_speed=45,
    )

    # Set return values
    DatabaseManager.is_connected = True
    mock_get_client.return_value = AsyncMock()
    mock_calc.return_value = fake.model_dump()

    # Call endpoint
    r = await async_client.get(
        "/api/gps_devices/dev1?date=2025-05-06",
        headers={
            str(VALID_SETTINGS_DATA["FASTAPI_API_KEY_HEADER"]): str(
                VALID_SETTINGS_DATA["FASTAPI_API_KEY"]
            )
        },
    )

    assert r.status_code == status.HTTP_200_OK
    assert r.json() == fake.model_dump()


@patch("src.fastapi.gps_devices.routes.gps_stats_service.calculate_stats")
@patch("src.fastapi.gps_devices.routes.db.get_client")
async def test_get_stats_invalid_date(
    mock_get_client, mock_calc, async_client: AsyncClient
):
    # invalid calendar date triggers ValueError -> GPSInvalidDateException -> 400
    DatabaseManager.is_connected = True
    mock_get_client.return_value = AsyncMock()

    r = await async_client.get(
        "/api/gps_devices/dev1?date=2025-02-30",
        headers={
            str(VALID_SETTINGS_DATA["FASTAPI_API_KEY_HEADER"]): str(
                VALID_SETTINGS_DATA["FASTAPI_API_KEY"]
            )
        },
    )
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid date" in r.json()["detail"]


@patch("src.fastapi.gps_devices.routes.gps_stats_service.calculate_stats")
@patch("src.fastapi.gps_devices.routes.db.get_client")
async def test_get_stats_not_found(
    mock_get_client, mock_calc, async_client: AsyncClient
):
    # not found exceptions -> 404
    DatabaseManager.is_connected = True
    mock_get_client.return_value = AsyncMock()

    # GPSNotFoundException
    mock_calc.side_effect = GPSNotFoundException(device_id="unknown", date="2025-05-06")
    r1 = await async_client.get(
        "/api/gps_devices/unknown?date=2025-05-06",
        headers={
            str(VALID_SETTINGS_DATA["FASTAPI_API_KEY_HEADER"]): str(
                VALID_SETTINGS_DATA["FASTAPI_API_KEY"]
            )
        },
    )
    assert r1.status_code == status.HTTP_404_NOT_FOUND

    # GPSDeviceNotFoundException
    mock_calc.side_effect = GPSDeviceNotFoundException(device_id="unknown2")
    r2 = await async_client.get(
        "/api/gps_devices/unknown2?date=2025-05-06",
        headers={
            str(VALID_SETTINGS_DATA["FASTAPI_API_KEY_HEADER"]): str(
                VALID_SETTINGS_DATA["FASTAPI_API_KEY"]
            )
        },
    )
    assert r2.status_code == status.HTTP_404_NOT_FOUND


@patch("src.fastapi.gps_devices.routes.gps_stats_service.calculate_stats")
@patch("src.fastapi.gps_devices.routes.db.get_client")
async def test_get_stats_unexpected_error(
    mock_get_client, mock_calc, async_client: AsyncClient
):
    # unexpected exception -> GPSException -> 500
    DatabaseManager.is_connected = True
    mock_get_client.return_value = AsyncMock()
    mock_calc.side_effect = RuntimeError("boom")

    r = await async_client.get(
        "/api/gps_devices/dev1?date=2025-05-06",
        headers={
            str(VALID_SETTINGS_DATA["FASTAPI_API_KEY_HEADER"]): str(
                VALID_SETTINGS_DATA["FASTAPI_API_KEY"]
            )
        },
    )
    assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "boom" in r.json()["detail"]


@pytest.mark.asyncio
async def test_calculate_vehicle_stats_success():
    t0 = datetime(2025, 5, 6, 0, 0, 0)

    e1 = MagicMock(timestamp=t0, odometer=0.0, speed=10.0)
    e2 = MagicMock(timestamp=t0 + timedelta(hours=1), odometer=100.0, speed=20.0)
    events = [e1, e2]

    mock_scalars_result1 = MagicMock()
    mock_scalars_result1.first.return_value = e1  # thiết bị tồn tại

    exists_res = MagicMock()
    exists_res.scalars.return_value = mock_scalars_result1

    mock_scalars_result2 = MagicMock()
    mock_scalars_result2.all.return_value = events

    events_res = MagicMock()
    events_res.scalars.return_value = mock_scalars_result2

    session = AsyncMock()
    session.execute.side_effect = [exists_res, events_res]

    result = await calculate_vehicle_stats(session, "dev1", datetime(2025, 5, 6))

    assert result["device_id"] == "dev1"
    assert result["date"] == "2025-05-06"
    assert result["total_distance_km"] == 100.0
    assert round(result["total_distance_miles"], 3) == round(100.0 * 0.621371, 3)
    assert result["average_speed"] == 15.0


async def test_calculate_vehicle_stats_device_not_found():
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = None
    execute_result = MagicMock()
    execute_result.scalars.return_value = mock_scalars

    session = AsyncMock()
    session.execute.return_value = execute_result

    with pytest.raises(GPSDeviceNotFoundException) as exc:
        await calculate_vehicle_stats(session, "missing", datetime(2025, 5, 6))

    assert "missing" in str(exc.value)


async def test_calculate_vehicle_stats_no_events():
    mock_first = MagicMock()
    mock_first.first.return_value = object()
    exists_res = MagicMock()
    exists_res.scalars.return_value = mock_first

    mock_all = MagicMock()
    mock_all.all.return_value = []
    events_res = MagicMock()
    events_res.scalars.return_value = mock_all

    session = AsyncMock()
    session.execute.side_effect = [exists_res, events_res]

    with pytest.raises(GPSNotFoundException) as exc:
        await calculate_vehicle_stats(session, "dev1", datetime(2025, 5, 6))

    assert "2025-05-06" in str(exc.value)


async def test_calculate_vehicle_stats_unexpected_error():
    session = AsyncMock()
    session.execute.side_effect = RuntimeError("db down!")

    with pytest.raises(GPSStatsException) as exc:
        await calculate_vehicle_stats(session, "dev1", datetime(2025, 5, 6))
    assert "db down!" in str(exc.value)
