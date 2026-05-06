"""Price alert poller Lambda."""

import logging
import os
from typing import Any, Dict

from bot.db.alerts import AlertsDB
from bot.utils.coingecko_client import CoinGeckoClient
from bot.utils.formatting import format_usd_value
from bot.utils.telegram import send_message

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def check_alert(direction: str, current_price: float, target_price: float) -> bool:
    """Return True if alert trigger condition is met."""
    if direction == "above":
        return current_price >= target_price
    if direction == "below":
        return current_price <= target_price
    return False


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    table = os.environ["DYNAMODB_TABLE"]
    region = os.getenv("AWS_REGION", "us-east-1")
    token = os.environ["TELEGRAM_TOKEN"]
    prices = CoinGeckoClient(os.getenv("COINGECKO_API_KEY"))
    db = AlertsDB(table, region=region)

    triggered = 0
    scanned = 0
    for alert in db.get_all_active_alerts():
        scanned += 1
        asset = alert.get("asset_symbol", "ETH").upper()
        target = float(alert.get("target_price", 0))
        direction = alert.get("direction", "above")
        user_id = str(alert.get("user_id"))

        current = prices.get_price(asset)
        if current is None:
            logger.warning("Price unavailable for %s", asset)
            continue
        if not check_alert(direction, current, target):
            continue

        triggered += 1
        db.delete_alert(alert.get("alert_id", ""), user_id=user_id)
        try:
            send_message(
                token,
                user_id,
                (
                    f"🔔 Price alert triggered: <b>{asset}</b>\n"
                    f"Current: {format_usd_value(current)}\n"
                    f"Target: {direction} {format_usd_value(target)}"
                ),
            )
        except Exception:
            logger.exception("Failed to notify user %s for alert", user_id)

    return {"statusCode": 200, "scanned": scanned, "triggered": triggered}

