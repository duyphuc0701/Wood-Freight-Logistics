import json
from datetime import date
from unittest.mock import AsyncMock, patch

import pendulum
import pytest

from src.fastapi.daily_summary.aggregator import DailyAggregator
from src.fastapi.daily_summary.schemas import DailyVehicleSummary, Trip
from src.fastapi.daily_summary.states import EngineState
from src.fastapi.daily_summary.strategies import (
    DefaultOperationalHoursStrategy,
    DefaultTripDefinitionStrategy,
    IOperationalHoursStrategy,
    ITripDefinitionStrategy,
)
from src.fastapi.rabbitmq_handlers.gps.schemas import GPSEventResponse


# region Fixtures
@pytest.fixture
def gps_event_response():
    return GPSEventResponse(
        device_id="device_123",
        device_name="device_name",
        timestamp=pendulum.datetime(2024, 5, 20, 8, 30),
        latitude=10.7769,
        longitude=106.6959,
        odometer=1000,
        power_on=True,
        speed=0,
        fuel_gauge=100.0,
    )


@pytest.fixture
def mock_trip_definition_strategy():
    class MockTripDefinitionStrategy(ITripDefinitionStrategy):
        def detect_trip(self, cached_daily_summary, event):
            return cached_daily_summary

    return MockTripDefinitionStrategy()


@pytest.fixture
def mock_operational_hours_strategy():
    class MockOperationalHoursStrategy(IOperationalHoursStrategy):
        def update_operational_hours(self, event, cached_daily_summary):
            return cached_daily_summary.total_operational_hours + 1

    return MockOperationalHoursStrategy()


@pytest.fixture
def gps_event():
    def _gps_event(
        device_id="device_123",
        timestamp=None,
        speed=0.0,
        power_on=True,
        latitude=10.7769,
        longitude=106.6959,
        odometer=1000.0,
        device_name="device_name",
        fuel_gauge=100.0,
    ):
        return GPSEventResponse(
            device_id=device_id,
            device_name=device_name,
            timestamp=timestamp
            or pendulum.datetime(2024, 5, 20, 8, 30, tz="Asia/Bangkok"),
            latitude=latitude,
            longitude=longitude,
            odometer=odometer,
            power_on=power_on,
            speed=speed,
            fuel_gauge=fuel_gauge,
        )

    return _gps_event


@pytest.fixture
def daily_summary():
    return DailyVehicleSummary(
        vehicle_id="device_123",
        summary_date=pendulum.date(2024, 5, 20),
        start_latitude=10.0,
        start_longitude=106.0,
        end_latitude=10.0,
        end_longitude=106.0,
        total_distance_km=0,
        total_operational_hours=0,
        trip_count=0,
        fuel_consumed_liters=5.0,
        odometer=1000,
        fuel_gauge=95.0,
        last_moving_time=None,
        last_event_time=pendulum.datetime(2024, 5, 20, 8, 30, tz="Asia/Bangkok"),
        state=EngineState.ENGINE_OFF,
        current_trip=None,
    )


# endregion


async def test_process_event_cache_miss(
    gps_event_response, mock_trip_definition_strategy, mock_operational_hours_strategy
):
    aggregator = DailyAggregator(
        trip_strategy=mock_trip_definition_strategy,
        operational_hours_strategy=mock_operational_hours_strategy,
    )

    with patch.object(
        aggregator, "get_cached_summary", AsyncMock(return_value=None)
    ), patch.object(aggregator, "save_summary_to_cache", AsyncMock()) as mock_save:
        await aggregator.process_event(gps_event_response)
        assert mock_save.call_count == 1
        summary_saved = mock_save.call_args[0][0]
        assert summary_saved.vehicle_id == gps_event_response.device_id
        assert summary_saved.start_latitude == gps_event_response.latitude
        assert summary_saved.state == EngineState.ENGINE_OFF


async def test_process_event_cache_hit(
    gps_event_response, mock_trip_definition_strategy, mock_operational_hours_strategy
):
    aggregator = DailyAggregator(
        trip_strategy=mock_trip_definition_strategy,
        operational_hours_strategy=mock_operational_hours_strategy,
    )

    cached_summary = DailyVehicleSummary(
        vehicle_id=gps_event_response.device_id,
        summary_date=gps_event_response.timestamp.date(),
        start_latitude=10.0,
        start_longitude=106.0,
        end_latitude=10.0,
        end_longitude=106.0,
        total_distance_km=0,
        total_operational_hours=0,
        trip_count=0,
        odometer=900,
        last_moving_time=None,
        last_event_time=pendulum.now().subtract(hours=1),
        state=EngineState.ENGINE_OFF,
    )

    with patch.object(
        aggregator, "get_cached_summary", AsyncMock(return_value=cached_summary)
    ), patch.object(aggregator, "save_summary_to_cache", AsyncMock()) as mock_save:
        await aggregator.process_event(gps_event_response)
        summary_saved = mock_save.call_args[0][0]
        assert summary_saved.end_latitude == gps_event_response.latitude
        assert summary_saved.total_distance_km == 100
        assert summary_saved.total_operational_hours == 1


def test_generate_key(mock_trip_definition_strategy, mock_operational_hours_strategy):
    aggregator = DailyAggregator(
        mock_trip_definition_strategy, mock_operational_hours_strategy
    )
    key = aggregator.generate_key("vehicle123", date(2024, 5, 20))
    assert key == "summary:vehicle123_2024-05-20"


@patch(
    "src.fastapi.daily_summary.aggregator.redis_manager.redis_client",
    new_callable=AsyncMock,
)
async def test_save_summary_to_cache(
    mock_redis_client, mock_trip_definition_strategy, mock_operational_hours_strategy
):
    aggregator = DailyAggregator(
        mock_trip_definition_strategy, mock_operational_hours_strategy
    )

    summary = DailyVehicleSummary(
        vehicle_id="device_123",
        summary_date=date.today(),
        start_latitude=10.0,
        start_longitude=106.0,
        end_latitude=10.0,
        end_longitude=106.0,
        total_distance_km=0,
        total_operational_hours=0,
        trip_count=0,
        fuel_consumed_liters=5.0,
        odometer=1000,
        fuel_gauge=95.0,
        last_moving_time=None,
        last_event_time=pendulum.now(),
        state=EngineState.ENGINE_OFF,
    )

    await aggregator.save_summary_to_cache(summary)
    key = aggregator.generate_key(summary.vehicle_id, summary.summary_date)
    mock_redis_client.setex.assert_called_once()
    assert key in aggregator.saved_keys


@patch("src.fastapi.daily_summary.aggregator.DailyVehicleSummary")
@patch(
    "src.fastapi.daily_summary.aggregator.redis_manager.redis_client",
    new_callable=AsyncMock,
)
async def test_get_cached_summary_found(
    mock_redis_client,
    mock_daily_vehicle_summary,
    mock_trip_definition_strategy,
    mock_operational_hours_strategy,
):
    summary_data = DailyVehicleSummary(
        vehicle_id="device_123",
        summary_date=date.today(),
        start_latitude=10.0,
        start_longitude=106.0,
        end_latitude=10.0,
        end_longitude=106.0,
        total_distance_km=0,
        total_operational_hours=0,
        trip_count=0,
        fuel_consumed_liters=5.0,
        odometer=1000,
        fuel_gauge=95.0,
        last_moving_time=None,
        last_event_time=pendulum.now(),
        state=EngineState.ENGINE_OFF,
    ).model_dump()

    mock_redis_client.get.return_value = json.dumps(summary_data, default=str)
    mock_daily_vehicle_summary.model_load.return_value = summary_data

    aggregator = DailyAggregator(
        mock_trip_definition_strategy, mock_operational_hours_strategy
    )
    result = await aggregator.get_cached_summary("device_123", date.today())

    assert result is not None


@patch(
    "src.fastapi.daily_summary.aggregator.redis_manager.redis_client",
    new_callable=AsyncMock,
)
async def test_get_cached_summary_not_found(
    mock_redis_client, mock_trip_definition_strategy, mock_operational_hours_strategy
):
    mock_redis_client.get.return_value = None

    aggregator = DailyAggregator(
        mock_trip_definition_strategy, mock_operational_hours_strategy
    )
    result = await aggregator.get_cached_summary("device_123", date.today())
    assert result is None


def test_default_trip_strategy_start_new_trip(gps_event, daily_summary):
    strategy = DefaultTripDefinitionStrategy(idle_threshold=300.0)
    event = gps_event(speed=10, power_on=True)

    result = strategy.detect_trip(daily_summary, event)

    assert result.current_trip is not None
    assert result.current_trip.start_time == event.timestamp
    assert result.last_moving_time == event.timestamp
    assert result.trip_count == 0


def test_default_trip_strategy_end_trip_after_idle(gps_event, daily_summary):
    strategy = DefaultTripDefinitionStrategy(idle_threshold=300.0)

    daily_summary.state = EngineState.ENGINE_MOVING
    daily_summary.current_trip = Trip(
        start_time=pendulum.datetime(2024, 5, 20, 8, 30, tz="Asia/Bangkok")
    )
    daily_summary.last_moving_time = pendulum.datetime(
        2024, 5, 20, 8, 30, tz="Asia/Bangkok"
    )

    later_event = gps_event(
        timestamp=pendulum.datetime(2024, 5, 20, 8, 36, tz="Asia/Bangkok"),
        speed=0,
        power_on=False,
    )

    result = strategy.detect_trip(daily_summary, later_event)

    assert result.current_trip is None
    assert result.last_moving_time is None
    assert result.trip_count == 1


def test_default_trip_strategy_no_trip_end_within_idle(gps_event, daily_summary):
    strategy = DefaultTripDefinitionStrategy(idle_threshold=300.0)

    daily_summary.state = EngineState.ENGINE_MOVING
    daily_summary.current_trip = Trip(
        start_time=pendulum.datetime(2024, 5, 20, 8, 30, tz="Asia/Bangkok")
    )
    daily_summary.last_moving_time = pendulum.datetime(
        2024, 5, 20, 8, 30, tz="Asia/Bangkok"
    )

    later_event = gps_event(
        timestamp=pendulum.datetime(2024, 5, 20, 8, 32, tz="Asia/Bangkok"),
        speed=0,
        power_on=True,
    )

    result = strategy.detect_trip(daily_summary, later_event)

    assert result.current_trip is not None
    assert result.last_moving_time is not None
    assert result.trip_count == 0


def test_default_trip_strategy_no_state_change(gps_event, daily_summary):
    strategy = DefaultTripDefinitionStrategy(idle_threshold=300.0)
    daily_summary.state = EngineState.ENGINE_OFF
    event = gps_event(speed=0, power_on=False)

    result = strategy.detect_trip(daily_summary, event)

    assert result.current_trip is None
    assert result.last_moving_time is None
    assert result.trip_count == 0


def test_operational_hours_strategy_engine_on(gps_event, daily_summary):
    strategy = DefaultOperationalHoursStrategy()
    daily_summary.state = EngineState.ENGINE_MOVING
    daily_summary.last_event_time = pendulum.datetime(
        2024, 5, 20, 8, 30, tz="Asia/Bangkok"
    )

    later_event = gps_event(
        timestamp=pendulum.datetime(2024, 5, 20, 9, 30, tz="Asia/Bangkok"),
        speed=10,
        power_on=True,
    )

    operational_hours = strategy.update_operational_hours(later_event, daily_summary)

    assert operational_hours == pytest.approx(1.0, abs=1e-6)


def test_operational_hours_strategy_engine_off(gps_event, daily_summary):
    strategy = DefaultOperationalHoursStrategy()
    daily_summary.state = EngineState.ENGINE_OFF
    daily_summary.last_event_time = pendulum.datetime(
        2024, 5, 20, 8, 30, tz="Asia/Bangkok"
    )

    later_event = gps_event(
        timestamp=pendulum.datetime(2024, 5, 20, 9, 30, tz="Asia/Bangkok"),
        speed=0,
        power_on=False,
    )

    operational_hours = strategy.update_operational_hours(later_event, daily_summary)

    assert operational_hours == 0.0


def test_operational_hours_strategy_first_event(gps_event_response, daily_summary):
    strategy = DefaultOperationalHoursStrategy()
    daily_summary.last_event_time = None
    daily_summary.state = EngineState.ENGINE_MOVING

    operational_hours = strategy.update_operational_hours(
        gps_event_response, daily_summary
    )

    assert operational_hours == 0.0
