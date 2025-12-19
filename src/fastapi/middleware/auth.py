import logging
from typing import cast

from fastapi import Request
from src.fastapi.config import get_settings
from src.fastapi.middleware.exceptions import InvalidAPIKeyError, MissingAPIKeyError

logger = logging.getLogger(__name__)
settings = get_settings()
FASTAPI_API_KEY_HEADER = settings.FASTAPI_API_KEY_HEADER
FASTAPI_API_KEY = settings.FASTAPI_API_KEY


async def validate_api_key(request: Request) -> str:
    """Middleware to validate API key for incoming requests."""
    api_key = request.headers.get(FASTAPI_API_KEY_HEADER)
    if not api_key:
        logger.warning("Missing API key in request")
        raise MissingAPIKeyError
    if api_key != FASTAPI_API_KEY:
        logger.warning(f"Invalid API key: {api_key}")
        raise InvalidAPIKeyError(api_key)
    logger.info("API key validated successfully")
    return cast(str, api_key)
