import asyncio
import json
import logging
import signal
from http import HTTPStatus
from typing import Awaitable, Optional, Union

from websockets.asyncio.server import ServerConnection, serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from websockets.http11 import Request, Response

from src.alert.config import get_settings
from src.alert.logging_config import setup_logging
from src.alert.redis.redis import redis_manager
from src.alert.schemas import AlertEvent
from src.alert.utils import process_alert

setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


def process_request(
    connection: ServerConnection, request: Request
) -> Union[Response, Awaitable[Optional[Response]], None]:
    if request.path == "/health":
        return Response(
            status_code=HTTPStatus.OK, reason_phrase="OK", headers=Headers(), body=b"OK"
        )
    return None


async def alerts_handler(websocket: ServerConnection):
    logger.info("Client connected to alert system")
    try:
        async for raw_msg in websocket:
            try:
                event = AlertEvent.model_validate_json(raw_msg)

            except Exception as e:
                logger.error(f"Invalid payload: {e}")

                await websocket.send(
                    json.dumps(
                        {
                            "status": "error",
                            "reason": str(e),
                        }
                    )
                )
                continue

            asyncio.create_task(process_alert(event))

            await websocket.send(
                json.dumps(
                    {
                        "status": "received",
                        "event_type": event.event_type,
                        "device_id": event.device_id,
                    }
                )
            )
    except ConnectionClosedOK:
        logger.info("Client disconnected cleanly")
    except ConnectionClosedError as e:
        logger.warning(f"Connection closed with error: {e}")
    except Exception as e:
        logger.exception(f"Unexpected handler error: {e}")


async def start_alert_server(host: str, port: int, shutdown_future: asyncio.Future):
    await redis_manager.init_redis()
    logger.info("Redis initialized; alerting service started.")

    async with serve(alerts_handler, host, port, process_request=process_request):
        logger.info(f"WebSocket server listening on ws://{host}:{port}")
        await shutdown_future
        await redis_manager.close_redis()
        logger.info("Alerting service stopped.")


async def main():
    shutdown = asyncio.Future()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown.set_result, None)

    port = settings.ALERTING_PORT or 8001
    await start_alert_server("0.0.0.0", port, shutdown)


def run_app():
    asyncio.run(main())


if __name__ == "__main__":
    run_app()
