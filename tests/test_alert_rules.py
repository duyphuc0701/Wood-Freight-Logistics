from datetime import datetime

from src.alert.rules import AlertRule, matches_rule
from src.alert.schemas import AlertEvent


def make_event(event_type: str, data: dict) -> AlertEvent:
    return AlertEvent(
        event_type=event_type,
        device_id="dev1",
        device_name="Device 1",
        timestamp=datetime.now().isoformat(),
        data=data,
    )


def test_matches_rule_numeric_threshold_pass(gps_rule):
    event = make_event("gps", {"speed": 70})
    assert matches_rule(event, gps_rule) is True


def test_matches_rule_numeric_threshold_fail(gps_rule):
    event = make_event("gps", {"speed": 50})
    assert matches_rule(event, gps_rule) is False


def test_matches_rule_list_threshold_pass(fault_rule):
    event = make_event("fault", {"fault_code": "2"})
    assert matches_rule(event, fault_rule) is True


def test_matches_rule_list_threshold_fail(fault_rule):
    event = make_event("fault", {"fault_code": "999"})
    assert matches_rule(event, fault_rule) is False


def test_matches_rule_wrong_event_type(fault_rule):
    event = make_event("gps", {"fault_code": "2"})
    assert matches_rule(event, fault_rule) is False


def test_matches_rule_missing_key(fault_rule):
    event = make_event("fault", {})
    assert matches_rule(event, fault_rule) is False


def test_matches_rule_direct_equality():
    rule = AlertRule(
        email="a@a.com", event_types=["custom"], thresholds={"status": "OK"}
    )
    event = make_event("custom", {"status": "OK"})
    assert matches_rule(event, rule) is True


def test_matches_rule_direct_equality_fail():
    rule = AlertRule(
        email="a@a.com", event_types=["custom"], thresholds={"status": "OK"}
    )
    event = make_event("custom", {"status": "FAIL"})
    assert matches_rule(event, rule) is False


def test_matches_rule_typeerror_on_numeric_threshold():
    rule = AlertRule(
        email="ops@example.com",
        event_types=["gps"],
        thresholds={"speed": 70.0},
    )
    event = make_event("gps", {"speed": "fast"})

    result = matches_rule(event, rule)
    assert result is False
