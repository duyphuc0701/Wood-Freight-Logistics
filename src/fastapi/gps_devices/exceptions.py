from http import HTTPStatus

from fastapi import HTTPException


class GPSException(HTTPException):
    """Base exception class for GPS-related errors."""

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    message = "An error occurred in GPS processing."

    def __init__(
        self,
        status_code: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR,
        message: str = "An error occurred in GPS processing.",
    ):
        self.status_code = status_code
        self.message = message or self.message
        super().__init__(status_code=status_code, detail=self.message)


class GPSStatsException(GPSException):
    """Exception for vehicle statistics calculation errors."""

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    message = "Failed to calculate vehicle statistics."

    def __init__(self, device_id: str, date: str, details: str = ""):
        self.device_id = device_id
        self.date = date
        self.details = details
        message = f"{self.message} Device ID: {device_id}, Date: {date}"
        if details and details != "":
            message += f" Details: {details}"
        super().__init__(status_code=self.status_code, message=message)


class GPSNotFoundException(GPSException):
    """Exception for when no GPS data is found for the specified device and date."""

    status_code = HTTPStatus.NOT_FOUND
    message = "No GPS data found for the specified device and date."

    def __init__(self, device_id: str, date: str):
        self.device_id = device_id
        self.date = date
        message = f"{self.message} Device ID: {device_id}, Date: {date}"
        super().__init__(status_code=self.status_code, message=message)


class GPSDeviceNotFoundException(GPSException):
    """Exception for when the device ID does not exist in the database."""

    status_code = HTTPStatus.NOT_FOUND
    message = "Device ID does not exist in the database."

    def __init__(self, device_id: str):
        self.device_id = device_id
        message = f"{self.message} Device ID: {device_id}"
        super().__init__(status_code=self.status_code, message=message)


class GPSInvalidDateException(GPSException):
    """Exception for invalid date format."""

    status_code = HTTPStatus.BAD_REQUEST
    message = "Invalid date format."

    def __init__(self, date: str):
        self.date = date
        message = f"{self.message} Provided date: {date}"
        super().__init__(status_code=self.status_code, message=message)
