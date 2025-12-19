import pytest

VALID_SETTINGS_DATA = {
    "ENVIRONMENT": "production",
    "FASTAPI_API_KEY_HEADER": "test_key_header",
    "FASTAPI_API_KEY": "test_key",
    "FASTAPI_CORS_ORIGINS": ["http://localhost"],
    "RABBITMQ_HOST": "localhost",
    "RABBITMQ_PORT": 5672,
    "RABBITMQ_USER": "guest",
    "RABBITMQ_PASSWORD": "guest",
    "REDIS_HOST": "redis",
    "REDIS_PORT": 6379,
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "postgres",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": 5432,
    "POSTGRES_DB": "postgres",
    "DEVICE_API_URL": "http://localhost:8000",
    "FAULT_API_URL": "http://localhost:8000",
    "ALERTING_HOST": "localhost",
    "ALERTING_PORT": 8080,
}
HEADERS = {
    VALID_SETTINGS_DATA["FASTAPI_API_KEY_HEADER"]: VALID_SETTINGS_DATA[
        "FASTAPI_API_KEY"
    ]
}


@pytest.fixture(scope="function", autouse=True)
def mock_get_settings(monkeypatch):
    """
    Mock the get_settings function to return a test configuration.
    """
    from src.fastapi.config import Settings, get_settings

    def _get_settings():
        return Settings(**VALID_SETTINGS_DATA)

    get_settings.cache_clear()
    monkeypatch.setattr("src.fastapi.database.database.get_settings", _get_settings)
    monkeypatch.setattr("src.fastapi.middleware.auth.get_settings", _get_settings)
    monkeypatch.setattr("src.fastapi.config.get_settings", _get_settings)
    monkeypatch.setattr("src.fastapi.main.get_settings", _get_settings)

    # Force reload the auth module to use the patched config
    import importlib

    import src.fastapi.database.database
    import src.fastapi.main
    import src.fastapi.middleware.auth

    importlib.reload(src.fastapi.main)
    importlib.reload(src.fastapi.middleware.auth)
    importlib.reload(src.fastapi.database.database)
