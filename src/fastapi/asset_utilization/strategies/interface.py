from abc import ABC, abstractmethod

from src.fastapi.asset_utilization.schemas import AssetUtilizationResponseDTO
from src.fastapi.daily_summary.schemas import DailyVehicleSummary


class IUtilizationStrategy(ABC):
    @abstractmethod
    def calculate(
        self, summary: DailyVehicleSummary
    ) -> AssetUtilizationResponseDTO: ...
