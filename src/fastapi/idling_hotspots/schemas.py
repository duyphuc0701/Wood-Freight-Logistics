from datetime import date, datetime
from typing import List

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class IdlingHotspotRequestDTO(BaseModel):
    date_range_start: date = Field(..., description="Start date for the report")
    date_range_end: date = Field(..., description="End date for the report")
    min_idle_duration_minutes: int = Field(
        ..., description="Minimum idle duration in minutes"
    )
    aggregation_level: str = Field(
        "rounded_lat_lon_0.01", description="Level of aggregation for hotspots"
    )
    page: int = Field(1, ge=1, description="Page number for pagination")
    page_size: int = Field(20, ge=1, le=100, description="Number of results per page")

    @field_validator("date_range_end")
    @classmethod
    def validate_date_range(cls, end: date, info: ValidationInfo):
        start = info.data.get("date_range_start")
        if start and end < start:
            raise ValueError(
                "date_range_end must be after or equal to date_range_start"
            )
        return end


class IdlingHotspotResponseDTO(BaseModel):
    location_identifier: str
    total_idle_incidents: int
    total_idle_duration_minutes: float
    contributing_asset_ids_sample: List[str]


class IdlingHotspot(BaseModel):
    id: int
    asset_id: str
    date: date
    idle_duration_minutes: float
    latitude: float
    longitude: float


class IdlingDetectedEvent(BaseModel):
    device_id: str
    start_time: datetime
    end_time: datetime
    latitude: float
    longitude: float
