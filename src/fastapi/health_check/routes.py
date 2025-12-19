import logging
from http import HTTPStatus

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

health_router = APIRouter(prefix="/health", tags=["Health Check"])


@health_router.get("")
async def health_check():
    """Check the health of the API."""
    logger.info("Health check requested")
    return JSONResponse(status_code=HTTPStatus.OK, content={"status": "ok"})
