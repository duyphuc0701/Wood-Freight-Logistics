import base64
import logging
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.fastapi.rabbitmq_handlers.fault.exceptions import FaultDecodeException

logger = logging.getLogger(__name__)


class FaultEventBase(BaseModel):
    """General schema for Fault event"""

    device_id: str = Field(..., min_length=1)
    timestamp: datetime = Field(..., description="UTC timestamp of Fault event")
    fault_bits: str = Field(..., min_length=1)
    fault_code: str = Field(..., min_length=1)
    sequence: int = Field(..., ge=0)
    total_number: int = Field(..., ge=0)


class FaultEventCreate(FaultEventBase):
    """Schema for creating a Fault segment event"""

    @classmethod
    def from_base64(cls, base64_str: str) -> "FaultEventCreate":
        try:
            decoded_bytes = base64.b64decode(base64_str)
            decoded_str = decoded_bytes.decode("utf-8")

            parts = decoded_str.split(":")
            if len(parts) != 6:
                raise ValueError(f"Expected 6 fields, got {len(parts)}")

            device_id, ts_str, fault_bits, code_str, seq_str, total_str = parts

            timestamp = datetime.fromtimestamp(float(ts_str))

            return cls(
                device_id=device_id,
                timestamp=timestamp,
                fault_bits=fault_bits,
                fault_code=code_str,
                sequence=int(seq_str),
                total_number=int(total_str),
            )

        except Exception as e:
            logger.error(f"Failed to decode base64 fault event: {e}")
            raise FaultDecodeException(base64_str, str(e))


class FaultEventResponse(BaseModel):
    device_id: str
    device_name: str
    timestamp: datetime
    fault_payload: str
    fault_code: str
    fault_label: str

    model_config = ConfigDict(from_attributes=True)
