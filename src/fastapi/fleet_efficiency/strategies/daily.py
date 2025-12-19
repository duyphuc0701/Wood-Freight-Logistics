from typing import List, Optional

from src.fastapi.daily_summary.schemas import DailyVehicleSummary
from src.fastapi.fleet_efficiency.schemas import DailyFleetEfficiencyRecordDTO
from src.fastapi.fleet_efficiency.strategies.interface import (
    IFleetEfficiencyAggregationStrategy,
)


class DailyAggregationStrategy(IFleetEfficiencyAggregationStrategy):
    async def aggregate(
        self, summaries: List[DailyVehicleSummary], asset_ids: Optional[List[str]]
    ) -> List[DailyFleetEfficiencyRecordDTO]:
        results = []

        for summary in summaries:
            fuel = summary.fuel_consumed_liters or 0.0
            km_per_liter = summary.total_distance_km / fuel if fuel > 0 else 0.0
            record = DailyFleetEfficiencyRecordDTO(
                asset_id=summary.vehicle_id,
                summary_date=summary.summary_date,
                traveled_km=summary.total_distance_km or 0.0,
                operational_hours=summary.total_operational_hours or 0.0,
                fuel_consumed_liters=fuel,
                km_per_liter=km_per_liter,
            )
            results.append(record)

        return results
