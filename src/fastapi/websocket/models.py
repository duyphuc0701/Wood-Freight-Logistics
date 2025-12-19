from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertEvent(BaseModel):
    """Schema for alert events sent to alerting system"""

    event_type: str
    device_id: str
    device_name: str
    timestamp: datetime
    data: dict

    model_config = ConfigDict(from_attributes=True)
