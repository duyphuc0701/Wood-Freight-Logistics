class FaultEventException(Exception):
    """Base exception class for Fault event processing errors."""

    message = "An error occurred during Fault event processing."

    def __init__(
        self, message: str = "An error occurred during Fault event processing."
    ):
        self.message = message or self.message
        super().__init__(self.message)


class FaultDecodeException(FaultEventException):
    def __init__(self, payload: str, reason: str):
        super().__init__(f"Failed to decode fault payload '{payload}': {reason}")


class FaultDeviceAPIException(FaultEventException):
    def __init__(self, device_id: str):
        super().__init__(f"Failed to fetch device name for device ID '{device_id}'")


class FaultCacheSegmentException(FaultEventException):
    def __init__(self, device_id: str, fault_code: str):
        super().__init__(
            f"Failed to cache fault segments from device ID "
            f"'{device_id}' with fault code '{fault_code}"
        )


class FaultConstructPayloadException(FaultEventException):
    def __init__(self, device_id: str, fault_code: str):
        super().__init__(
            f"Failed to construct whole fault payload from device ID "
            f"'{device_id}' with fault code '{fault_code}"
        )


class FaultLabelAPIException(FaultEventException):
    def __init__(self, fault_code: str):
        super().__init__(f"Failed to fetch label for fault code '{fault_code}'")


class FaultDatabaseSaveException(FaultEventException):
    def __init__(self, device_id: str, fault_code: str):
        super().__init__(
            f"Failed to save fault event to database with device ID "
            f"'{device_id}' and fault code '{fault_code}"
        )


class FaultSendAlertException(FaultEventException):
    def __init__(self, fault_code: str):
        super().__init__(
            f"Failed to send fault event to alerting system with "
            f"fault code '{fault_code}"
        )


class FaultRateLimitException(FaultLabelAPIException):
    """Exception for Device API rate limit errors."""

    message = "Rate limit exceeded for Device API."

    def __init__(self, fault_code: str):
        super().__init__(fault_code)
