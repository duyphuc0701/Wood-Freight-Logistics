from abc import ABC, abstractmethod

from src.fastapi.daily_summary.schemas import DailyVehicleSummary, Trip
from src.fastapi.daily_summary.states import EngineState, get_state
from src.fastapi.rabbitmq_handlers.gps.schemas import GPSEventResponse


class ITripDefinitionStrategy(ABC):
    @abstractmethod
    def detect_trip(
        self, current_daily_summary: DailyVehicleSummary, event: GPSEventResponse
    ) -> DailyVehicleSummary:
        """Detect ended trip and update trip count"""
        pass


# Concrete Strategy for Trip Counting (based on previous logic)
class DefaultTripDefinitionStrategy(ITripDefinitionStrategy):
    def __init__(self, idle_threshold: float = 300.0):
        self.idle_threshold = idle_threshold  # Seconds (e.g., 5 minutes)

    def detect_trip(
        self, current_daily_summary: DailyVehicleSummary, event: GPSEventResponse
    ) -> DailyVehicleSummary:
        current_state = current_daily_summary.state
        new_state = get_state(event.power_on, event.speed)
        timestamp = event.timestamp

        # Handle state transitions
        if new_state != current_state:
            if new_state == EngineState.ENGINE_MOVING:
                # Start a new trip
                current_daily_summary.current_trip = Trip(start_time=timestamp)
                current_daily_summary.last_moving_time = timestamp

        if (
            new_state in (EngineState.ENGINE_OFF, EngineState.ENGINE_ON_STATIONARY)
            and current_daily_summary.last_moving_time
            and current_daily_summary.current_trip
        ):
            duration = (
                timestamp - current_daily_summary.last_moving_time
            ).total_seconds()
            if duration >= self.idle_threshold:
                # End the current trip
                current_daily_summary.current_trip.complete_trip(end_time=timestamp)
                current_daily_summary.trip_count += 1
                current_daily_summary.current_trip = None
                current_daily_summary.last_moving_time = None

        return current_daily_summary


class IOperationalHoursStrategy(ABC):
    @abstractmethod
    def update_operational_hours(
        self, event: GPSEventResponse, current_daily_summary: DailyVehicleSummary
    ) -> float:
        """Update and return the total operational hours"""
        pass


class DefaultOperationalHoursStrategy(IOperationalHoursStrategy):
    def __init__(self):
        self.last_event_time = None

    def update_operational_hours(
        self, event: GPSEventResponse, current_daily_summary: DailyVehicleSummary
    ) -> float:
        current_state = current_daily_summary.state
        last_event_time = current_daily_summary.last_event_time
        timestamp = event.timestamp
        operational_hours = current_daily_summary.total_operational_hours

        if last_event_time is None:
            last_event_time = timestamp
            return operational_hours

        # Calculate time delta since last event
        delta = (timestamp - last_event_time).total_seconds() / 3600.0

        # Add to operational hours if engine was on (stationary or moving)
        if current_state in (
            EngineState.ENGINE_ON_STATIONARY,
            EngineState.ENGINE_MOVING,
        ):
            operational_hours += delta

        return operational_hours
