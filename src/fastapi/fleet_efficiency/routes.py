from typing import Annotated, List

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Query, Response
from src.fastapi.database.dependencies import verify_database
from src.fastapi.fleet_efficiency.dependencies import get_fleet_efficiency_service
from src.fastapi.fleet_efficiency.schemas import (
    FleetEfficiencyRequestDTO,
    FleetEfficiencyResponseDTO,
)
from src.fastapi.fleet_efficiency.services import FleetEfficiencyService

fleet_efficiency_router = APIRouter(tags=["Fleet Efficiency Report"])


@fleet_efficiency_router.get(
    "/fleet-efficiency", response_model=FleetEfficiencyResponseDTO
)
async def get_fleet_efficiency(
    response: Response,
    db_session: AsyncSession = Depends(verify_database),
    params: FleetEfficiencyRequestDTO = Depends(),
    asset_ids: Annotated[List[str] | None, Query()] = None,
    service: FleetEfficiencyService = Depends(get_fleet_efficiency_service),
):
    results, total = await service.get_efficiency_report(db_session, params, asset_ids)

    # Calculate total pages
    total_pages = (total + params.page_size - 1) // params.page_size

    # Set pagination headers
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str(total_pages)
    response.headers["X-Current-Page"] = str(params.page)
    response.headers["X-Page-Size"] = str(params.page_size)

    return results
