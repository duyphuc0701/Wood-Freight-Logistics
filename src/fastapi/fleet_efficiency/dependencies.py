from src.fastapi.fleet_efficiency.repositories.fuel_consumption import (
    DailyFuelConsumptionRepository,
)
from src.fastapi.fleet_efficiency.services import FleetEfficiencyService

fuel_consumption_repo = DailyFuelConsumptionRepository()
service = FleetEfficiencyService(fuel_consumption_repo)


def get_fleet_efficiency_service() -> FleetEfficiencyService:
    return service
