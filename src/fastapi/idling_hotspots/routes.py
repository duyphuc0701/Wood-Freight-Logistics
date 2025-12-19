from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Response
from src.fastapi.database.dependencies import verify_database
from src.fastapi.idling_hotspots.dependencies import get_idling_report_service
from src.fastapi.idling_hotspots.schemas import (
    IdlingHotspotRequestDTO,
    IdlingHotspotResponseDTO,
)
from src.fastapi.idling_hotspots.services import IdlingReportService

idling_hotspots_router = APIRouter(tags=["Vehicle Idling Hotspot"])


@idling_hotspots_router.get(
    "/idling-hotspots", response_model=List[IdlingHotspotResponseDTO]
)
async def get_idling_hotspots(
    response: Response,
    db_session: AsyncSession = Depends(verify_database),
    params: IdlingHotspotRequestDTO = Depends(),
    service: IdlingReportService = Depends(get_idling_report_service),
):
    results, total = await service.get_idling_hotspots_report(
        db_session=db_session, params=params
    )
    # Calculate total pages
    total_pages = (total + params.page_size - 1) // params.page_size

    # Set pagination headers
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str(total_pages)
    response.headers["X-Current-Page"] = str(params.page)
    response.headers["X-Page-Size"] = str(params.page_size)

    return results
