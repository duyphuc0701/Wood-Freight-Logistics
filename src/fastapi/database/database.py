import asyncio
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import text

from src.fastapi.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
POSTGRES_HOST = settings.POSTGRES_HOST
POSTGRES_PORT = settings.POSTGRES_PORT
POSTGRES_DB = settings.POSTGRES_DB
POSTGRES_USER = settings.POSTGRES_USER
POSTGRES_PASSWORD = settings.POSTGRES_PASSWORD


# Define the base class for SQLAlchemy models
Base = declarative_base()

# Setup PostgreSQL connection URI
DATABASE_URL = (
    f"postgresql+asyncpg://{POSTGRES_USER}:"
    f"{POSTGRES_PASSWORD}@{POSTGRES_HOST}:"
    f"{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Create async engine and sessionmaker
engine = create_async_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class DatabaseManager:
    is_connected: bool = False
    retry_interval: int = 5  # seconds

    @classmethod
    async def connect(cls):
        """Connect to PostgreSQL database"""
        try:
            if cls.is_connected:
                logger.info("Already connected to the database")
                return
            async with engine.connect() as conn:
                await conn.scalar(text("SELECT 1"))  # Simple test query
            cls.is_connected = True
            logger.info("Database connection established")
        except SQLAlchemyError as e:
            cls.is_connected = False
            logger.error(f"Database connection failed: {str(e)}")
            raise e

    @classmethod
    async def disconnect(cls):
        """Disconnect from database"""
        if cls.is_connected:
            await engine.dispose()
            cls.is_connected = False
            logger.info("Database connection closed")

    @classmethod
    async def reconnect(cls, max_attempts: int = 1):
        attempts = 0
        while not cls.is_connected and attempts < max_attempts:
            try:
                await cls.connect()
            except Exception as e:
                logger.error(f"Reconnection attempt failed: {str(e)}")
                await asyncio.sleep(cls.retry_interval)
                attempts += 1
        if not cls.is_connected:
            raise SQLAlchemyError("Max reconnection attempts exceeded")

    @classmethod
    async def get_client(cls) -> AsyncSession:
        if not cls.is_connected:
            logger.error("Database is not connected")
            raise RuntimeError("Database is not connected")
        return SessionLocal()

    @classmethod
    async def list_tables(cls):
        """List all tables in the database"""
        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        "SELECT table_name "
                        "FROM information_schema.tables "
                        "WHERE table_schema = 'public'"
                    )
                )
                tables = [row[0] for row in await result.fetchall()]
                logger.info(f"Tables in database: {tables}")
                return tables
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            raise


db = DatabaseManager()
