from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.fastapi.daily_summary.models import DailyVehicleSummaryModel
from src.fastapi.daily_summary.states import EngineState


class Trip(BaseModel):
    start_time: datetime
    end_time: Optional[datetime] = None
    operational_hours: float = 0.0

    def complete_trip(self, end_time: datetime):
        self.end_time = end_time
        self.operational_hours = (end_time - self.start_time).total_seconds() / 3600.0


class DailyVehicleSummary(BaseModel):
    vehicle_id: str = Field(..., max_length=50)
    summary_date: date
    start_latitude: float = 0.0
    start_longitude: float = 0.0
    end_latitude: float = 0.0
    end_longitude: float = 0.0
    total_distance_km: float = 0.0
    total_operational_hours: float = 0.0
    trip_count: int = 0
    fuel_consumed_liters: float = 0.0
    odometer: float = 0.0
    fuel_gauge: float = 100.0
    last_moving_time: Optional[datetime] = None
    last_event_time: Optional[datetime] = None
    state: EngineState = EngineState.ENGINE_OFF
    current_trip: Optional[Trip] = None

    def to_model(self) -> DailyVehicleSummaryModel:
        return DailyVehicleSummaryModel(
            vehicle_id=self.vehicle_id,
            summary_date=self.summary_date,
            start_latitude=self.start_latitude,
            start_longitude=self.start_longitude,
            end_latitude=self.end_latitude,
            end_longitude=self.end_longitude,
            total_distance_km=self.total_distance_km,
            total_operational_hours=self.total_operational_hours,
            trip_count=self.trip_count,
            fuel_consumed_liters=self.fuel_consumed_liters,
        )
