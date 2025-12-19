import base64
from datetime import datetime

import pytest

from src.fastapi.rabbitmq_handlers.fault.schemas import (
    FaultDecodeException,
    FaultEventCreate,
)


def encode_colon_payload(parts: list[str]) -> str:
    """
    Join the list by ":" and base64-encode the result.
    """
    raw = ":".join(parts)
    return base64.b64encode(raw.encode("utf-8")).decode("utf-8")


def test_from_base64_valid_fields():
    # Given a well-formed colon-delimited payload
    parts = ["1", "1617181920", "10101010", "3", "2", "5"]
    b64 = encode_colon_payload(parts)

    event = FaultEventCreate.from_base64(b64)

    expected_ts = datetime.fromtimestamp(float(parts[1]))

    assert isinstance(event, FaultEventCreate)
    assert event.device_id == parts[0]
    assert event.timestamp == expected_ts
    assert event.fault_bits == parts[2]
    assert event.fault_code == parts[3]
    assert event.sequence == int(parts[4])
    assert event.total_number == int(parts[5])


@pytest.mark.parametrize(
    "raw_str, exc_msg",
    [
        ("not-a-valid-base64!!!", "Invalid base64"),
        (encode_colon_payload(["a", "b", "c"]), "Expected 6 fields"),
        (
            encode_colon_payload(["a", "b", "c", "d", "e", "f", "g"]),
            "Expected 6 fields",
        ),
        (
            encode_colon_payload(["dev", "ts", "bits", "code", "X", "1"]),
            "invalid literal",
        ),
        (
            encode_colon_payload(["dev", "ts", "bits", "code", "0", "Y"]),
            "invalid literal",
        ),
    ],
)
def test_from_base64_invalid(raw_str, exc_msg):
    with pytest.raises(FaultDecodeException) as excinfo:
        FaultEventCreate.from_base64(raw_str)
    # The original base64 string should appear in the exception message
    assert raw_str in str(excinfo.value)
