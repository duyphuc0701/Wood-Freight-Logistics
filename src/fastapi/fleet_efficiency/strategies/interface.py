from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel

from src.fastapi.daily_summary.schemas import DailyVehicleSummary

T = TypeVar("T", bound=BaseModel)


class IFleetEfficiencyAggregationStrategy(ABC, Generic[T]):
    @abstractmethod
    async def aggregate(
        self, summaries: List[DailyVehicleSummary], asset_ids: Optional[List[str]]
    ) -> List[T]:
        """
        Abstract method to aggregate fleet efficiency data.
        """
        ...
