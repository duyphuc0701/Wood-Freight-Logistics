from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Union

from src.fastapi.daily_summary.schemas import DailyVehicleSummary
from src.fastapi.fleet_efficiency.schemas import (
    AssetPeriodEfficiencyDTO,
    FleetAggregatedEfficiencyDTO,
)
from src.fastapi.fleet_efficiency.strategies.interface import (
    IFleetEfficiencyAggregationStrategy,
)


class WeeklyAggregationStrategy(IFleetEfficiencyAggregationStrategy):
    def _get_week_start(self, d: date) -> date:
        return d - timedelta(days=d.weekday())

    async def aggregate(
        self,
        summaries: List[DailyVehicleSummary],
        asset_ids: Optional[List[str]],
    ) -> List[Union[FleetAggregatedEfficiencyDTO, AssetPeriodEfficiencyDTO]]:
        data: Dict[Tuple[str, date], List[DailyVehicleSummary]] = defaultdict(list)
        all_weeks: Dict[date, set] = defaultdict(set)

        for summary in summaries:
            week_start = self._get_week_start(summary.summary_date)
            key = (summary.vehicle_id if asset_ids else "fleet", week_start)
            data[key].append(summary)
            all_weeks[week_start].add(summary.vehicle_id)

        results: List[Union[FleetAggregatedEfficiencyDTO, AssetPeriodEfficiencyDTO]] = (
            []
        )

        for (key_id, period_start), records in data.items():
            period_end = period_start + timedelta(days=6)
            total_km = sum(r.total_distance_km or 0.0 for r in records)
            total_hours = sum(r.total_operational_hours or 0.0 for r in records)
            total_fuel = sum(r.fuel_consumed_liters or 0.0 for r in records)

            if not asset_ids:
                # Fleet-level aggregation (1 record per week)
                num_assets = len(all_weeks[period_start])
                avg_hours = (total_hours / (7 * num_assets)) if num_assets else 0.0
                km_per_liter = total_km / total_fuel if total_fuel > 0 else None

                results.append(
                    FleetAggregatedEfficiencyDTO(
                        period_start=period_start,
                        period_end=period_end,
                        total_traveled_km_fleet=total_km,
                        average_operational_hours_per_asset_per_day=avg_hours,
                        overall_km_per_liter_fleet=km_per_liter,
                    )
                )
            else:
                # Per-asset aggregation (1 record per asset per week)
                km_per_liter = total_km / total_fuel if total_fuel > 0 else None

                results.append(
                    AssetPeriodEfficiencyDTO(
                        period_start=period_start,
                        period_end=period_end,
                        asset_id=key_id,
                        total_traveled_km=total_km,
                        total_operational_hours=total_hours,
                        km_per_liter=km_per_liter,
                    )
                )

        return results
