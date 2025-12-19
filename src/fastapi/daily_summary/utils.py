from datetime import datetime


def seconds_since_midnight(dt: datetime):
    # Extract time components
    return (
        (dt.hour * 3600) + (dt.minute * 60) + dt.second + (dt.microsecond / 1_000_000)
    )
