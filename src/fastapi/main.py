import asyncio
import logging
from contextlib import asynccontextmanager
from http import HTTPStatus

import aio_pika
from sqlalchemy.exc import SQLAlchemyError

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from src.fastapi.asset_utilization.routes import asset_utilization_router
from src.fastapi.config import get_settings
from src.fastapi.daily_summary.repositories import DailySummaryRepository
from src.fastapi.daily_summary.scheduler import DailySummaryScheduler
from src.fastapi.database.database import Base, DatabaseManager, db, engine
from src.fastapi.fleet_efficiency.routes import fleet_efficiency_router
from src.fastapi.gps_devices.routes import gps_router
from src.fastapi.health_check.routes import health_router
from src.fastapi.idling_hotspots.routes import idling_hotspots_router
from src.fastapi.logging_config import setup_logging
from src.fastapi.rabbitmq_handlers.fault.handler import handle_fault_event
from src.fastapi.rabbitmq_handlers.gps.handler import handle_gps_event
from src.fastapi.redis.redis import redis_manager

setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()
PROJECT_NAME = settings.PROJECT_NAME
FastAPI_API_KEY_HEADER = settings.FASTAPI_API_KEY_HEADER
ALL_CORS_ORIGINS = settings.all_cors_origins
RABBITMQ_HOST = settings.RABBITMQ_HOST
RABBITMQ_PORT = settings.RABBITMQ_PORT
RABBITMQ_USER = settings.RABBITMQ_USER
RABBITMQ_PASSWORD = settings.RABBITMQ_PASSWORD
RABBITMQ_URL = (
    f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@" f"{RABBITMQ_HOST}:{RABBITMQ_PORT}/"
)


# Initialize the database engine
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Custom OpenAPI schema to include API key security
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=PROJECT_NAME,
        version="0.1.0",
        description="API for managing tasks with API key security",
        routes=app.routes,
    )

    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    openapi_schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": FastAPI_API_KEY_HEADER,
        }
    }

    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", []).append({"APIKeyHeader": []})

    app.openapi_schema = openapi_schema
    return app.openapi_schema


async def consume_queue(channel, queue_name):
    queue = await channel.declare_queue(queue_name, durable=True)
    async with await db.get_client() as db_session:
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        payload = message.body.decode()

                        if payload:
                            if queue_name == "gps_queue":
                                logger.info("Consume GPS event")
                                await handle_gps_event(db_session, payload)
                            elif queue_name == "fault_queue":
                                logger.info("Consume fault event")
                                await handle_fault_event(db_session, payload)
                            else:
                                logger.warning(f"Unknown queue: {queue_name}")

                    except Exception as e:
                        logger.error(
                            f"[{queue_name}] Failed to process message: " f"{str(e)}"
                        )


async def ingest_event():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()

    # Declare the exchange (direct type for routing via routing key)
    exchange = await channel.declare_exchange(
        "events_exchange", aio_pika.ExchangeType.DIRECT, durable=True
    )

    # Declare and bind GPS queue
    gps_queue = await channel.declare_queue("gps_queue", durable=True)
    await gps_queue.bind(exchange, routing_key="gps")

    # Declare and bind Fault queue
    fault_queue = await channel.declare_queue("fault_queue", durable=True)
    await fault_queue.bind(exchange, routing_key="fault")

    # Create two tasks to consume from both queues
    gps_task = asyncio.create_task(consume_queue(channel, "gps_queue"))
    fault_task = asyncio.create_task(consume_queue(channel, "fault_queue"))

    # Keep them alive
    await asyncio.gather(gps_task, fault_task)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    try:
        await DatabaseManager.connect()
        await init_db()
        await redis_manager.init_redis()
        daily_summary_repo = DailySummaryRepository()
        loop = asyncio.get_running_loop()
        daily_summary_scheduler = DailySummaryScheduler(daily_summary_repo, loop)

        # Create background task for RabbitMQ consumer
        app.state.rabbitmq_consumer_task = asyncio.create_task(ingest_event())

        daily_summary_scheduler.run()

        logger.info("Startup complete")
        yield

        logger.info("Shutting down...")

        # Cancel the RabbitMQ consumer task
        app.state.rabbitmq_consumer_task.cancel()
        try:
            await app.state.rabbitmq_consumer_task
        except asyncio.CancelledError:
            logger.info("RabbitMQ consumer task cancelled.")

        await redis_manager.close_redis()
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise
    finally:
        await DatabaseManager.disconnect()
        logger.info("Shutdown complete")


app = FastAPI(title=PROJECT_NAME, version="0.1.0", lifespan=lifespan)
app.openapi = custom_openapi  # type: ignore[method-assign]


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        content={
            "detail": "Database connection error. Please try again later.",
            "error": str(exc),
        },
    )


# Set all CORS enabled origins
if ALL_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALL_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# API Routes
api_router = APIRouter(prefix="/api")
api_router.include_router(gps_router)
api_router.include_router(asset_utilization_router)
api_router.include_router(fleet_efficiency_router)
api_router.include_router(idling_hotspots_router)
app.include_router(api_router)
app.include_router(health_router)
