from datetime import date
from typing import Literal, Union

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator


class AssetUtilizationRequestDTO(BaseModel):
    report_by: Literal["distance", "hours"]
    target_km_per_day: float | None = None
    target_hours_per_day: float | None = None
    date_range_start: date = Field(date.today(), description="YYYY-MM-DD")
    date_range_end: date = Field(date.today(), description="YYYY-MM-DD")
    page: int = 1
    page_size: int = 20
    sort_by: str = "vehicle_id"
    sort_order: str = "asc"

    @field_validator("report_by")
    @classmethod
    def validate_report_by(cls, value: str) -> str:
        allowed = {"distance", "hours"}
        if value not in allowed:
            raise ValueError(f"report_by must be one of {allowed}")
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

    @model_validator(mode="after")
    def validate_targets(self) -> "AssetUtilizationRequestDTO":
        if self.report_by == "distance":
            if self.target_km_per_day is None:
                raise ValueError(
                    "target_km_per_day is required " "when report_by is 'distance'"
                )
            self.target_hours_per_day = None  # hide from output
        elif self.report_by == "hours":
            if self.target_hours_per_day is None:
                raise ValueError(
                    "target_hours_per_day is required " "when report_by is 'hours'"
                )
            self.target_km_per_day = None  # hide from output
        return self


class AssetUtilizationDTO(BaseModel):
    asset_id: str
    summary_date: date
    utilization_score_primary: float


class DistanceUtilDTO(AssetUtilizationDTO):
    actual_traveled_km: float
    target_km_met: bool


class HoursUtilDTO(AssetUtilizationDTO):
    actual_operational_hours: float
    target_hours_met: bool


AssetUtilizationResponseDTO = Union[DistanceUtilDTO, HoursUtilDTO]
