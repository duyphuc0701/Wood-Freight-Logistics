from src.fastapi.fleet_efficiency.enums import Granularity
from src.fastapi.fleet_efficiency.strategies.daily import DailyAggregationStrategy
from src.fastapi.fleet_efficiency.strategies.interface import (
    IFleetEfficiencyAggregationStrategy,
)
from src.fastapi.fleet_efficiency.strategies.monthly import MonthlyAggregationStrategy
from src.fastapi.fleet_efficiency.strategies.weekly import WeeklyAggregationStrategy


class FleetEfficiencyStrategyFactory:
    @staticmethod
    def create(granularity: Granularity) -> IFleetEfficiencyAggregationStrategy:
        if granularity == Granularity.daily:
            return DailyAggregationStrategy()
        elif granularity == Granularity.weekly:
            return WeeklyAggregationStrategy()
        elif granularity == Granularity.monthly:
            return MonthlyAggregationStrategy()
        else:
            raise ValueError("Unsupported granularity")
