from typing import Any, Dict

from pydantic import BaseModel, ConfigDict


class AlertEvent(BaseModel):
    """Schema for alert events sent to alerting system"""

    event_type: str
    device_id: str
    device_name: str
    timestamp: str
    data: Dict[str, Any]

    # Allow population from attribute names
    model_config = ConfigDict(from_attributes=True)
