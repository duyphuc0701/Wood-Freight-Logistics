from pydantic import BaseModel, ConfigDict


class GPSStatsResponse(BaseModel):
    """Schema for vehicle statistics response."""

    device_id: str
    date: str
    total_distance_km: float
    total_distance_miles: float
    average_speed: float

    model_config = ConfigDict(from_attributes=True)
