from src.fastapi.asset_utilization.strategies.distance_metric import (
    DistanceUtilizationStrategy,
)
from src.fastapi.asset_utilization.strategies.hours_metric import (
    HoursUtilizationStrategy,
)
from src.fastapi.asset_utilization.strategies.interface import IUtilizationStrategy


class UtilizationStrategyFactory:
    @staticmethod
    def create(
        report_by: str,
        target_km_per_day: float | None = None,
        target_hours_per_day: float | None = None,
    ) -> IUtilizationStrategy:
        if report_by == "distance":
            if target_km_per_day is None:
                raise ValueError("target_km_per_day is required")
            return DistanceUtilizationStrategy(target_km_per_day)
        elif report_by == "hours":
            if target_hours_per_day is None:
                raise ValueError("target_hours_per_day is required")
            return HoursUtilizationStrategy(target_hours_per_day)
        else:
            raise ValueError(f"Unsupported report_by value: {report_by}")
