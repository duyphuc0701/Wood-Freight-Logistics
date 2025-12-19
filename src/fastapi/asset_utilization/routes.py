from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Response
from src.fastapi.asset_utilization.dependencies import get_utilization_service
from src.fastapi.asset_utilization.schemas import (
    AssetUtilizationRequestDTO,
    AssetUtilizationResponseDTO,
)
from src.fastapi.asset_utilization.services import UtilizationReportService
from src.fastapi.database.dependencies import verify_database

asset_utilization_router = APIRouter(
    prefix="/asset-utilization", tags=["Asset Utilization"]
)


@asset_utilization_router.get("", response_model=list[AssetUtilizationResponseDTO])
async def get_asset_utilization(
    response: Response,
    db_session: AsyncSession = Depends(verify_database),
    params: AssetUtilizationRequestDTO = Depends(),
    service: UtilizationReportService = Depends(get_utilization_service),
):
    results, total = await service.generate_report(db_session, params)

    # Calculate total pages
    total_pages = (total + params.page_size - 1) // params.page_size

    # Set pagination headers
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str(total_pages)
    response.headers["X-Current-Page"] = str(params.page)
    response.headers["X-Page-Size"] = str(params.page_size)

    return results
