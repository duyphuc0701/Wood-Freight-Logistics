import asyncio
import base64
import logging

from src.alert.notifications import send_email
from src.alert.redis.redis import redis_manager
from src.alert.rules import RULES, matches_rule
from src.alert.schemas import AlertEvent

logger = logging.getLogger(__name__)


async def check_suppression_period(fault_code: str, payload: bytes) -> bool:
    try:
        last_2_bytes = payload[-2:]
        suppression_secs = int.from_bytes(last_2_bytes, byteorder="big")

        cache_key = f"suppression:{fault_code}"
        if redis_manager.redis_client:
            existing = await redis_manager.redis_client.get(cache_key)

            if existing:
                logger.info(
                    f"Fault {fault_code} on device suppressed "
                    f"(still within {suppression_secs}s window)"
                )
                return True

            await redis_manager.redis_client.setex(
                cache_key, suppression_secs, "suppressed"
            )
            logger.info(
                f"Started suppression for fault {fault_code} on device "
                f"for {suppression_secs}s"
            )
            return False
    except Exception as e:
        logger.error(f"Suppression check error: {str(e)}")

    return False


async def process_alert(event: AlertEvent):
    """
    Applies suppression, evaluates rules, and dispatches notifications.
    """
    # Fault suppression
    if event.event_type == "fault":
        fault_code = event.data.get("fault_code", "")
        b64_fault_payload = event.data.get("fault_payload", "")

        payload_bytes = base64.b64decode(b64_fault_payload)
        try:
            if await check_suppression_period(
                fault_code=fault_code, payload=payload_bytes
            ):
                logger.info(
                    f"Suppressed fault {fault_code}" f"for device {event.device_id}"
                )
                return
        except Exception as e:
            logger.warning(f"Suppression check failed: {e}")

    # Rule evaluation
    matching_rules = [rule for rule in RULES if matches_rule(event, rule)]
    if not matching_rules:
        logger.info(f"No matching rules for event: {event}")
        return

    # Dispatch notifications
    payload_json = event.model_dump_json()
    for rule in matching_rules:
        try:
            data = event.model_dump().get("data", {})

            subject_parts: list[str] = []
            for key, configured in rule.thresholds.items():
                if key not in data:
                    continue

                actual = data[key]
                subject_parts.append(f"{key}={actual} (threshold={configured})")

            if subject_parts:
                detail = ", ".join(subject_parts)
            else:
                detail = "no matching thresholds"

            subject = f"Alert: {event.event_type} [{detail}]"

            asyncio.create_task(send_email(rule.email, subject, payload_json))
            logger.info(f"Scheduled notification for {rule.email}")

        except Exception as e:
            logger.error(f"Failed to schedule notification for {rule.email}: {e}")
