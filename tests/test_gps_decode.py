import base64
from datetime import datetime

import pytest

from src.fastapi.rabbitmq_handlers.gps.schemas import GPSDecodeException, GPSEventCreate


def encode_colon_payload(parts: list[str]) -> str:
    return base64.b64encode(":".join(parts).encode()).decode()


def test_from_base64_valid_payload():
    parts = ["dev123", "1617181920.0", "55.5", "1000.2", "True", "0", "0", "0"]
    b64 = encode_colon_payload(parts)

    event = GPSEventCreate.from_base64(b64)

    expected_ts = datetime.fromtimestamp(float(parts[1]))
    assert isinstance(event, GPSEventCreate)
    assert event.device_id == parts[0]
    assert event.timestamp == expected_ts
    assert event.speed == float(parts[2])
    assert event.odometer == float(parts[3])
    assert event.power_on is True
    assert event.latitude == float(parts[5])
    assert event.longitude == float(parts[6])
    assert event.fuel_gauge == float(parts[7])


@pytest.mark.parametrize(
    "raw_str, error_fragment",
    [
        ("not-a-valid-base64!", "Invalid base64"),
        (encode_colon_payload(["dev", "ts", "55.5"]), "not enough values to unpack"),
        (
            encode_colon_payload(
                ["dev", "ts", "55.5", "1000", "True", "0", "0", "0", "extra"]
            ),
            "too many values to unpack",
        ),
        (
            encode_colon_payload(
                ["dev", "bad_float", "55.5", "1000", "True", "0", "0", "0"]
            ),
            "could not convert string to float",
        ),
        (
            encode_colon_payload(
                ["dev", "1617181920.0", "fast", "1000", "True", "0", "0", "0"]
            ),
            "could not convert string to float",
        ),
        (
            encode_colon_payload(
                ["dev", "1617181920.0", "55.5", "broken", "True", "0", "0", "0"]
            ),
            "could not convert string to float",
        ),
    ],
)
def test_from_base64_invalid_payload(raw_str, error_fragment):
    with pytest.raises(GPSDecodeException) as excinfo:
        GPSEventCreate.from_base64(raw_str)

    assert raw_str in str(excinfo.value)


def test_from_base64_strips_quotes():
    # Normal GPS payload
    parts = ["dev999", "1617181920.0", "60.0", "1234.5", "False", "0", "0", "0"]
    raw_payload = ":".join(parts)

    # Wrap with quotes
    quoted = f'"{raw_payload}"'
    b64 = base64.b64encode(quoted.encode("utf-8")).decode()

    event = GPSEventCreate.from_base64(b64)

    expected_ts = datetime.fromtimestamp(float(parts[1]))

    assert event.device_id == parts[0]
    assert event.timestamp == expected_ts
    assert event.speed == float(parts[2])
    assert event.odometer == float(parts[3])
    assert event.power_on is False
    assert event.latitude == float(parts[5])
    assert event.longitude == float(parts[6])
    assert event.fuel_gauge == float(parts[7])
