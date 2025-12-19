class GPSEventException(Exception):
    """Base exception class for GPS event processing errors."""

    message = "An error occurred during GPS event processing."

    def __init__(self, message: str = "An error occurred during GPS event processing."):
        self.message = message or self.message
        super().__init__(self.message)


class GPSDecodeException(GPSEventException):
    """Exception for base64 decoding errors."""

    message = "Failed to decode base64 GPS event."

    def __init__(self, payload: str, details: str = ""):
        self.payload = payload
        self.details = details
        message = f"{self.message} Payload: {payload}"
        if details != "":
            message += f" Details: {details}"
        super().__init__(message)


class GPSRedisException(GPSEventException):
    """Exception for Redis operation errors."""

    message = "Failed to perform Redis operation."

    def __init__(self, operation: str, key: str, details: str = ""):
        self.operation = operation
        self.key = key
        self.details = details
        message = f"{self.message} Operation: {operation}, Key: {key}"
        if details != "":
            message += f" Details: {details}"
        super().__init__(message)


class GPSDeviceAPIException(GPSEventException):
    """Exception for Device API errors."""

    message = "Failed to fetch device name from API."

    def __init__(self, device_id: str, status_code: int = -1, details: str = ""):
        self.device_id = device_id
        self.status_code = status_code
        self.details = details
        message = f"{self.message} Device ID: {device_id}"
        if status_code != -1:
            message += f", Status Code: {status_code}"
        if details != "":
            message += f" Details: {details}"
        super().__init__(message)


class GPSRateLimitException(GPSDeviceAPIException):
    """Exception for Device API rate limit errors."""

    message = "Rate limit exceeded for Device API."

    def __init__(self, device_id: str):
        super().__init__(device_id, status_code=429)


class GPSDatabaseException(GPSEventException):
    """Exception for database operation errors."""

    message = "Failed to save GPS event to database."

    def __init__(self, device_id: str, timestamp: str, details: str = ""):
        self.device_id = device_id
        self.timestamp = timestamp
        self.details = details
        message = f"{self.message} Device ID: {device_id}, Timestamp: {timestamp}"
        if details != "":
            message += f" Details: {details}"
        super().__init__(message)


class GPSRedisNotInitializedException(GPSEventException):
    """Exception for Redis client not initialized."""

    message = "Redis client is not initialized."

    def __init__(self, operation: str):
        self.operation = operation
        message = f"{self.message} Attempted operation: {operation}"
        super().__init__(message)
