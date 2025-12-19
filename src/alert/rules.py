from dataclasses import dataclass
from typing import Any, Dict, List

from src.alert.schemas import AlertEvent


@dataclass
class AlertRule:
    email: str
    event_types: List[str]
    thresholds: Dict[str, Any]


# Define your alert rules here
RULES: List[AlertRule] = [
    AlertRule(
        email="example@gmail.com",
        event_types=["fault"],
        thresholds={
            # only alert on these fault codes
            "fault_code": [str(i) for i in range(1, 101)]
        },
    ),
    AlertRule(
        email="example@gmail.com",
        event_types=["gps"],
        thresholds={
            # Numeric threshold
            "speed": 70.0
        },
    ),
]


def matches_rule(event: AlertEvent, rule: AlertRule) -> bool:
    """
    Returns True if the AlertEvent matches the given AlertRule.

    Numeric thresholds in rule.thresholds are treated as '>= threshold'.
    List thresholds require membership. Other types require equality.
    """
    # Check event type
    if event.event_type not in rule.event_types:
        return False

    for key, threshold in rule.thresholds.items():
        value = event.data.get(key)
        if value is None:
            return False

        # Numeric threshold (int or float)
        if isinstance(threshold, (int, float)):
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return False
            if numeric < float(threshold):
                return False

        # List threshold (membership)
        elif isinstance(threshold, list):
            if value not in threshold:
                return False

        # Direct equality
        else:
            if value != threshold:
                return False

    return True
