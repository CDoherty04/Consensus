"""Scheduled payment runner Lambda."""

import datetime as dt
import logging
import os
from typing import Any, Dict

from bot.db.contacts import ContactsDB
from bot.db.scheduled_payments import ScheduledPaymentsDB
from bot.db.user_state import UserStateDB
from bot.utils.telegram import send_message
from bot.wallet.x402_client import X402Client

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def calculate_next_run(current_ts: int, recurrence: str) -> int:
    """Calculate next execution timestamp."""
    now = dt.datetime.fromtimestamp(current_ts, tz=dt.timezone.utc)
    if recurrence == "daily":
        return int((now + dt.timedelta(days=1)).timestamp())
    if recurrence == "weekly":
        return int((now + dt.timedelta(days=7)).timestamp())
    if recurrence == "monthly":
        return int((now + dt.timedelta(days=30)).timestamp())
    return current_ts


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    table = os.environ["DYNAMODB_TABLE"]
    region = os.getenv("AWS_REGION", "us-east-1")
    token = os.environ["TELEGRAM_TOKEN"]
    x402 = X402Client(private_key=os.environ["X402_PRIVATE_KEY"])
    user_db = UserStateDB(table, region=region)
    contacts_db = ContactsDB(table, region=region)
    payments_db = ScheduledPaymentsDB(table, region=region)

    processed = 0
    succeeded = 0
    failed = 0

    for payment in payments_db.get_due_payments():
        processed += 1
        user_id = str(payment.get("user_id"))
        payment_id = payment.get("payment_id")
        recurrence = payment.get("recurrence", "once")

        try:
            user = user_db.get_user(user_id)
            if not user:
                raise ValueError("User record missing.")
            contacts = contacts_db.get_contacts(user_id)
            contact_id = payment.get("contact_id")
            contact = next((c for c in contacts if c.get("contact_id") == contact_id), None)
            if not contact:
                raise ValueError("Contact not found for payment.")

            tx_hash = x402.send_transaction(
                from_address=user.get("wallet_address"),
                to_address=contact.get("address"),
                amount=float(payment.get("amount", 0)),
                token=payment.get("currency", "USDC"),
            )

            if recurrence == "once":
                payments_db.delete_payment(payment_id, user_id=user_id)
            else:
                payments_db.update_next_run(
                    payment_id,
                    calculate_next_run(int(payment.get("next_run", 0)), recurrence),
                    user_id=user_id,
                )

            succeeded += 1
            prefs = user.get("notification_prefs", {})
            if prefs.get("scheduled_payments", True):
                send_message(
                    token,
                    user_id,
                    (
                        "✅ Scheduled payment executed\n"
                        f"{payment.get('amount')} {payment.get('currency')} to {contact.get('name')}\n"
                        f"Tx: <code>{tx_hash}</code>"
                    ),
                )
        except Exception as exc:
            failed += 1
            logger.exception("Scheduled payment failed: %s", payment_id)
            try:
                send_message(
                    token,
                    user_id,
                    f"❌ Scheduled payment failed ({payment_id}): {exc}",
                )
            except Exception:
                logger.exception("Failed to send payment failure notice")

    return {
        "statusCode": 200,
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
    }

