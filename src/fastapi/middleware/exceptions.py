from http import HTTPStatus
from typing import Optional

from fastapi import HTTPException


class MiddlewareException(HTTPException):
    """Base exception class for middleware errors."""

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    message = "An error occurred."

    def __init__(
        self,
        status_code: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR,
        message: str = "An error occurred.",
    ):
        self.status_code = status_code
        self.message = message
        super().__init__(status_code, message)


class MissingAPIKeyError(MiddlewareException):
    """Raised when an API key is missing."""

    status_code = HTTPStatus.UNAUTHORIZED
    message = "Missing API key."

    def __init__(self):
        super().__init__(self.status_code, self.message)


class InvalidAPIKeyError(MiddlewareException):
    """Raised when an invalid API key is provided."""

    status_code = HTTPStatus.FORBIDDEN
    message = "Invalid API key provided."

    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            self.message += f" ID: {api_key}"
        super().__init__(self.status_code, self.message)
