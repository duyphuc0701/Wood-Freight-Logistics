from src.fastapi.asset_utilization.schemas import DistanceUtilDTO
from src.fastapi.asset_utilization.strategies.interface import IUtilizationStrategy
from src.fastapi.daily_summary.schemas import DailyVehicleSummary


class DistanceUtilizationStrategy(IUtilizationStrategy):
    def __init__(self, target_km: float):
        self.target_km = target_km

    def calculate(self, summary: DailyVehicleSummary):
        score = (
            summary.total_distance_km / self.target_km
            if summary.total_distance_km
            else 0.0
        )
        return DistanceUtilDTO(
            asset_id=summary.vehicle_id,
            summary_date=summary.summary_date,
            actual_traveled_km=summary.total_distance_km,
            target_km_met=(score >= 1.0),
            utilization_score_primary=round(min(score, 1.0), 2),
        )
