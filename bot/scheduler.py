"""Scheduled payment CRUD and recurrence utilities."""

import datetime as dt
from typing import Dict, List, Optional

from bot.db.scheduled_payments import ScheduledPaymentsDB
from bot.utils.validation import validate_amount, validate_currency, validate_recurrence


class PaymentSchedulerService:
    """Manage scheduled payments in user state."""

    def __init__(self, db: ScheduledPaymentsDB):
        self.db = db

    def create_payment(
        self,
        user_id: str,
        contact_id: str,
        amount: float,
        currency: str,
        recurrence: str,
        cron_or_datetime: Optional[str] = None,
    ) -> str:
        amount_ok, amount_error = validate_amount(amount)
        if not amount_ok:
            raise ValueError(amount_error or "Invalid amount.")
        currency_ok, currency_error = validate_currency(currency)
        if not currency_ok:
            raise ValueError(currency_error or "Invalid currency.")
        recurrence_ok, recurrence_error = validate_recurrence(recurrence)
        if not recurrence_ok:
            raise ValueError(recurrence_error or "Invalid recurrence.")

        next_run = self.calculate_next_run(
            recurrence=recurrence, cron_or_datetime=cron_or_datetime
        )
        return self.db.create_payment(
            user_id=user_id,
            contact_id=contact_id,
            amount=float(amount),
            currency=currency.upper(),
            recurrence=recurrence.lower(),
            next_run=next_run,
        )

    def list_payments(self, user_id: str) -> List[Dict]:
        return self.db.get_payments(user_id)

    def cancel_payment(self, user_id: str, payment_id: str) -> None:
        self.db.delete_payment(payment_id, user_id=user_id)

    @staticmethod
    def calculate_next_run(recurrence: str, cron_or_datetime: Optional[str] = None) -> int:
        now = dt.datetime.now(dt.timezone.utc)
        if cron_or_datetime:
            try:
                parsed = dt.datetime.fromisoformat(cron_or_datetime.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=dt.timezone.utc)
                return int(parsed.timestamp())
            except ValueError:
                pass

        recurrence = recurrence.lower()
        if recurrence == "once":
            return int((now + dt.timedelta(minutes=5)).timestamp())
        if recurrence == "daily":
            return int((now + dt.timedelta(days=1)).timestamp())
        if recurrence == "weekly":
            return int((now + dt.timedelta(days=7)).timestamp())
        if recurrence == "monthly":
            return int((now + dt.timedelta(days=30)).timestamp())
        raise ValueError("Unsupported recurrence.")

