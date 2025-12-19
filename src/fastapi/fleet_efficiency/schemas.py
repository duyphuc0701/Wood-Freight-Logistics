from datetime import date
from typing import List, Optional, Union

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from src.fastapi.fleet_efficiency.enums import Granularity


class FleetEfficiencyRequestDTO(BaseModel):
    date_range_start: date = Field(..., description="Start date in YYYY-MM-DD format")
    date_range_end: date = Field(..., description="End date in YYYY-MM-DD format")
    granularity: Granularity = Field(
        Granularity.daily, description="Granularity (daily, weekly, or monthly)"
    )
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1)

    @field_validator("granularity")
    @classmethod
    def validate_granularity(cls, value: str) -> str:
        allowed = {Granularity.daily, Granularity.weekly, Granularity.monthly}
        if value not in allowed:
            raise ValueError(f"granularity must be one of {allowed}")
        return value

    @field_validator("date_range_end")
    @classmethod
    def validate_date_range(cls, end: date, info: ValidationInfo):
        start = info.data.get("date_range_start")
        if start and end < start:
            raise ValueError(
                "date_range_end must be after or equal to date_range_start"
            )
        return end


class DailyFleetEfficiencyRecordDTO(BaseModel):
    asset_id: str
    summary_date: date
    traveled_km: float
    operational_hours: float
    fuel_consumed_liters: float
    km_per_liter: float


class AggregatedRecordDTO(BaseModel):
    period_start: date
    period_end: date


class FleetAggregatedEfficiencyDTO(AggregatedRecordDTO):
    total_traveled_km_fleet: float
    average_operational_hours_per_asset_per_day: float
    overall_km_per_liter_fleet: Optional[float]


class AssetPeriodEfficiencyDTO(AggregatedRecordDTO):
    asset_id: str
    total_traveled_km: float
    total_operational_hours: float
    km_per_liter: Optional[float]


FleetEfficiencyResponseDTO = Union[
    List[DailyFleetEfficiencyRecordDTO],
    List[Union[FleetAggregatedEfficiencyDTO, AssetPeriodEfficiencyDTO]],
]
