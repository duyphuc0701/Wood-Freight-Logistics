from src.fastapi.asset_utilization.schemas import HoursUtilDTO
from src.fastapi.asset_utilization.strategies.interface import IUtilizationStrategy
from src.fastapi.daily_summary.schemas import DailyVehicleSummary


class HoursUtilizationStrategy(IUtilizationStrategy):
    def __init__(self, target_hours: float):
        self.target_hours = target_hours

    def calculate(self, summary: DailyVehicleSummary):
        score = (
            summary.total_operational_hours / self.target_hours
            if summary.total_operational_hours
            else 0.0
        )
        return HoursUtilDTO(
            asset_id=summary.vehicle_id,
            summary_date=summary.summary_date,
            actual_operational_hours=summary.total_operational_hours,
            target_hours_met=(score >= 1.0),
            utilization_score_primary=round(min(score, 1.0), 2),
        )
