from unittest.mock import MagicMock

import pytest

from fastapi import Request
from src.fastapi.middleware.auth import validate_api_key
from src.fastapi.middleware.exceptions import InvalidAPIKeyError, MissingAPIKeyError
from tests.mocks.config_mocks import mock_get_settings  # noqa: F401
from tests.mocks.config_mocks import VALID_SETTINGS_DATA


async def test_validate_api_key_success(mock_get_settings):
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {
        VALID_SETTINGS_DATA["FASTAPI_API_KEY_HEADER"]: VALID_SETTINGS_DATA[
            "FASTAPI_API_KEY"
        ]
    }

    result = await validate_api_key(mock_request)
    assert result == VALID_SETTINGS_DATA["FASTAPI_API_KEY"]


async def test_validate_api_key_missing(mock_get_settings):
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {}  # No header

    with pytest.raises(MissingAPIKeyError):
        await validate_api_key(mock_request)


async def test_validate_api_key_invalid(mock_get_settings):
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {
        VALID_SETTINGS_DATA["FASTAPI_API_KEY_HEADER"]: "wrong-key"
    }  # Invalid key

    with pytest.raises(InvalidAPIKeyError) as exc:
        await validate_api_key(mock_request)
    assert "wrong-key" in str(exc.value)
