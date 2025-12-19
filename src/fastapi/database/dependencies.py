from fastapi import HTTPException, status

from .database import db


async def verify_database():
    """Verify database connection"""
    if not db.is_connected:
        try:
            await db.reconnect()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection is not available",
            )
    return await db.get_client()
