import base64
import logging
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.fastapi.rabbitmq_handlers.gps.exceptions import GPSDecodeException

logger = logging.getLogger(__name__)


class GPSEventBase(BaseModel):
    """General schema for GPSEvent"""

    device_id: str = Field(..., min_length=1)
    timestamp: datetime = Field(...)
    speed: float = Field(..., ge=0)
    odometer: float = Field(..., ge=0)
    power_on: bool
    latitude: float = Field(...)
    longitude: float = Field(...)
    fuel_gauge: float = Field(...)


class GPSEventCreate(GPSEventBase):
    """Schema used when creating GPSEvent from base64"""

    @classmethod
    def from_base64(cls, payload: str) -> "GPSEventCreate":
        try:
            decoded_data = base64.b64decode(payload).decode("utf-8")
            if decoded_data.startswith('"') and decoded_data.endswith('"'):
                decoded_data = decoded_data[1:-1]
            logger.info(f"Decoded data: {decoded_data}")
            (
                device_id,
                str_timestamp,
                speed,
                odometer,
                power_on,
                latitude,
                longitude,
                fuel_gauge,
            ) = decoded_data.split(":")
            timestamp = datetime.fromtimestamp(float(str_timestamp))
            logger.info(f"Device ID: {device_id}")
            return cls(
                device_id=device_id,
                timestamp=timestamp,
                speed=float(speed),
                odometer=float(odometer),
                power_on=power_on.lower() == "true",
                latitude=float(latitude),
                longitude=float(longitude),
                fuel_gauge=float(fuel_gauge),
            )
        except Exception as e:
            logger.error(f"Failed to decode base64 event: {str(e)}")
            raise GPSDecodeException(payload, str(e))


class GPSEventResponse(GPSEventBase):
    """Schema used when returning GPSEvent"""

    device_name: str

    model_config = ConfigDict(from_attributes=True)
