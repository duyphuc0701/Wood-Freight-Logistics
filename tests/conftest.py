from contextlib import asynccontextmanager

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.alert.rules import AlertRule
from src.fastapi.database.database import DATABASE_URL, Base, DatabaseManager
from src.fastapi.main import app
from tests.mocks.config_mocks import mock_get_settings  # noqa: F401

# -----------------------------------------------------------------------------
# DATABASE SETUP & CLEANUP
# -----------------------------------------------------------------------------
engine = create_async_engine(DATABASE_URL, echo=True)
test_engine = create_async_engine(DATABASE_URL, echo=True)


# Create async engine and sessionmaker for testing
def get_test_engine():
    return test_engine


# Create Async Session
AsyncTestSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=get_test_engine(),
    class_=AsyncSession,
)


@pytest.fixture(scope="module")
async def db_session():
    async with AsyncTestSessionLocal() as session:
        yield session


@pytest.fixture(scope="module", autouse=True)
async def setup_test_db(request):
    """
    Only setup and teardown the real DB if `use_real_database` is marked.
    Otherwise, skip DB setup entirely.
    """
    if "use_real_database" not in request.node.keywords:
        yield
        return

    await DatabaseManager.connect()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await DatabaseManager.disconnect()


@pytest.fixture(scope="function")
async def cleanup_each_test(request):
    yield
    if "cleanup_each_test" not in request.node.keywords:
        return

    try:
        async with test_engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(table.delete())
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            pass
        else:
            raise


# -----------------------------------------------------------------------------
# FASTAPI CLIENT FOR API TESTING
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_openapi_schema():
    app.openapi_schema = None
    yield
    app.openapi_schema = None


@pytest.fixture(scope="function")
async def async_client():
    """
    Provide an async client for FastAPI test with lifespan events.
    """

    @asynccontextmanager
    async def test_lifespan(_):
        yield

    app.router.lifespan_context = test_lifespan
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
def gps_rule():
    return AlertRule(
        email="alert@example.com", event_types=["gps"], thresholds={"speed": 60.0}
    )


@pytest.fixture
def fault_rule():
    return AlertRule(
        email="alert@example.com",
        event_types=["fault"],
        thresholds={"fault_code": ["1", "2", "3"]},
    )
