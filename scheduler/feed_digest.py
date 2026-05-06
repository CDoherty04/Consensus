"""Feed digest runner Lambda."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List

try:
    from anthropic import Anthropic
except Exception:  # pragma: no cover
    Anthropic = None  # type: ignore

from bot.db.subscriptions import SubscriptionsDB
from bot.feeds import FeedService
from bot.utils.telegram import send_message

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def summarize_content(api_key: str, content_items: List[Dict[str, str]]) -> str:
    """Summarize feed content via Claude with local fallback."""
    if not content_items:
        return ""

    if Anthropic and api_key:
        try:
            client = Anthropic(api_key=api_key)
            prompt = (
                "Summarize these feed items in concise bullets for a daily digest:\n\n"
                + "\n\n".join(
                    f"Title: {i['title']}\nURL: {i['url']}\nSummary: {i.get('summary','')}"
                    for i in content_items
                )
            )
            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            text = []
            for block in resp.content:
                if getattr(block, "type", "") == "text":
                    text.append(getattr(block, "text", ""))
            if text:
                return "\n".join(text).strip()
        except Exception:
            logger.exception("Claude summarization failed, using fallback.")

    lines = ["🗞️ Daily Feed Digest"]
    for item in content_items[:5]:
        lines.append(f"• {item['title']} — {item['url']}")
    return "\n".join(lines)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    table = os.environ["DYNAMODB_TABLE"]
    region = os.getenv("AWS_REGION", "us-east-1")
    token = os.environ["TELEGRAM_TOKEN"]
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    db = SubscriptionsDB(table, region=region)
    feed_service = FeedService(db)
    processed = 0
    sent = 0

    for sub in db.get_all_subscriptions():
        processed += 1
        user_id = str(sub.get("user_id"))
        feed_url = sub.get("feed_url", "")
        subscription_id = sub.get("subscription_id")

        try:
            items = feed_service.fetch_recent_items(feed_url, limit=5)
            if not items:
                continue
            digest = summarize_content(anthropic_key, items)
            if not digest:
                continue
            send_message(token, user_id, digest)
            sent += 1
            db.update_last_fetched(subscription_id, int(time.time()), user_id=user_id)
        except Exception:
            logger.exception("Feed digest processing failed for subscription %s", subscription_id)

    return {"statusCode": 200, "processed": processed, "sent": sent}

