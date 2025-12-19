import logging

import websockets
from tenacity import retry, stop_after_attempt, wait_fixed

from src.fastapi.config import get_settings
from src.fastapi.websocket.models import AlertEvent

logger = logging.getLogger(__name__)
settings = get_settings()
ALERTING_HOST = settings.ALERTING_HOST
ALERTING_PORT = settings.ALERTING_PORT
ALERTING_URL = f"ws://{ALERTING_HOST}:{ALERTING_PORT}"


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def send_alert_event(alert_event: AlertEvent):
    """
    Send an AlertEvent to the alerting system via WebSocket.
    """
    try:
        async with websockets.connect(ALERTING_URL) as websocket:
            # Serialize AlertEvent to JSON
            payload = alert_event.model_dump_json()
            await websocket.send(payload)
            logger.info(
                f"Sent alert event to WebSocket: {alert_event.event_type} "
                f"(device: {alert_event.device_id})"
            )

            # Wait for response from alerting container
            response = await websocket.recv()
            if isinstance(response, bytes):
                response = response.decode("utf-8")
            logger.info(f"Received response from alerting container: {response}")

            return response
    except Exception as e:
        logger.error(f"Failed to send alert event to {ALERTING_URL}: {str(e)}")
        raise
