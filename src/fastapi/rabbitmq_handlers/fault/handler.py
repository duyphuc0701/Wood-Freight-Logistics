import base64
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.fastapi.rabbitmq_handlers.fault.exceptions import (
    FaultCacheSegmentException,
    FaultConstructPayloadException,
    FaultDatabaseSaveException,
    FaultDecodeException,
    FaultDeviceAPIException,
    FaultLabelAPIException,
    FaultSendAlertException,
)
from src.fastapi.rabbitmq_handlers.fault.schemas import (
    FaultEventCreate,
    FaultEventResponse,
)
from src.fastapi.rabbitmq_handlers.fault.utils import (
    assemble_all_fault_segments,
    cache_fault_segment,
    fetch_fault_label,
    save_fault_event,
)
from src.fastapi.rabbitmq_handlers.gps.exceptions import GPSDeviceAPIException
from src.fastapi.rabbitmq_handlers.gps.utils import fetch_device_name
from src.fastapi.websocket.client import send_alert_event
from src.fastapi.websocket.models import AlertEvent

logger = logging.getLogger(__name__)


async def handle_fault_event(db: AsyncSession, payload: str) -> dict:
    try:
        fault_event = FaultEventCreate.from_base64(payload)
    except Exception as e:
        logger.error(f"Fault decode error: {str(e)}")
        return {"error": str(FaultDecodeException(payload=payload, reason=str(e)))}

    try:
        device_name = await fetch_device_name(fault_event.device_id)
        if not device_name:
            logger.error(f"Device name not found for {fault_event.device_id}")
            return {"error": str(GPSDeviceAPIException(fault_event.device_id))}
    except Exception as e:
        logger.error(f"Device API error: {str(e)}")
        return {"error": str(FaultDeviceAPIException(fault_event.device_id))}

    device_id = fault_event.device_id
    timestamp = fault_event.timestamp
    fault_bits = fault_event.fault_bits
    fault_code = fault_event.fault_code
    sequence = fault_event.sequence
    total_number = fault_event.total_number

    # Cache fault segment
    try:
        parts_received = await cache_fault_segment(
            device_id, fault_code, timestamp, sequence, fault_bits
        )
    except Exception as e:
        logger.error(f"Error caching fault segment for {device_id}/{fault_code}: {e}")
        return {"error": str(FaultCacheSegmentException(device_id, fault_code))}

    # Check if enough segments are received
    if parts_received < total_number:
        logger.info(
            f"[{device_id}] Fault {fault_code}: segment {sequence+1}/{total_number}, "
            f"{parts_received}/{total_number} stored, awaiting remainder"
        )
        return {"status": "pending", "received": parts_received, "total": total_number}

    # Construct the whole fault payload
    try:
        fault_payload, payload_bytes = await assemble_all_fault_segments(
            device_id, fault_code, timestamp, total_number
        )
    except Exception as e:
        logger.error(
            f"Error constructing fault payload for " f"{device_id}/{fault_code}: {e}"
        )
        return {"error": str(FaultConstructPayloadException(device_id, fault_code))}

    # Fetch the human-readable label for this fault code
    try:
        fault_label = await fetch_fault_label(fault_code)
    except Exception as e:
        logger.error(f"Fault label API error for code {fault_code}: {e}")
        return {"error": str(FaultLabelAPIException(fault_code))}

    result = {
        "device_id": device_id,
        "device_name": device_name,
        "timestamp": timestamp,
        "fault_payload": fault_payload,
        "fault_code": fault_code,
        "fault_label": fault_label,
    }

    # Save to database
    try:
        fault_event_resp = FaultEventResponse(**result)
        await save_fault_event(db, fault_event_resp)
    except Exception as e:
        logger.error(f"Error saving FaultEvent to DB for {device_id}/{fault_code}: {e}")
        return {"error": str(FaultDatabaseSaveException(device_id, fault_code))}

    # Change fault payload to bytes for alerting
    b64_payload_bytes = base64.b64encode(payload_bytes).decode("ascii")

    result["fault_payload"] = b64_payload_bytes

    # Send to alerting system via WebSocket
    alert_event = AlertEvent(
        event_type="fault",
        device_id=device_id,
        device_name=device_name,
        timestamp=timestamp,
        data=result,
    )
    try:
        await send_alert_event(alert_event)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        return {"error": str(FaultSendAlertException(fault_code))}

    return result
