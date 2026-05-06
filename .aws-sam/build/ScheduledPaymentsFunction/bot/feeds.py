"""Feed subscription and fetch utilities."""

import datetime as dt
import xml.etree.ElementTree as ET
from typing import Dict, List

import requests

from bot.db.subscriptions import SubscriptionsDB
from bot.utils.validation import validate_url


class FeedService:
    """Manage feed subscriptions and parse RSS content."""

    def __init__(self, db: SubscriptionsDB):
        self.db = db

    def subscribe(self, user_id: str, feed_url: str) -> str:
        valid, error = validate_url(feed_url)
        if not valid:
            raise ValueError(error or "Invalid feed URL.")
        return self.db.create_subscription(user_id, feed_url.strip())

    def unsubscribe(self, user_id: str, subscription_id: str) -> None:
        self.db.delete_subscription(subscription_id, user_id=user_id)

    def list_subscriptions(self, user_id: str) -> List[Dict]:
        return self.db.get_subscriptions(user_id)

    def fetch_recent_items(self, feed_url: str, limit: int = 5) -> List[Dict]:
        response = requests.get(feed_url, timeout=20)
        response.raise_for_status()
        root = ET.fromstring(response.text)

        items: List[Dict] = []
        for item in root.findall(".//item")[:limit]:
            title = (item.findtext("title") or "Untitled").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            summary = (item.findtext("description") or "").strip()
            items.append(
                {
                    "title": title,
                    "url": link,
                    "published": pub_date or dt.datetime.now(dt.timezone.utc).isoformat(),
                    "summary": summary,
                }
            )
        return items

    @staticmethod
    def search_articles(topic: str) -> List[Dict]:
        base = "https://example-paywalled-news.com"
        query = topic.replace(" ", "-").lower()
        return [
            {
                "title": f"{topic.title()} market outlook",
                "url": f"{base}/articles/{query}-outlook",
            },
            {
                "title": f"Deep dive: {topic.title()} trends",
                "url": f"{base}/articles/{query}-deep-dive",
            },
            {
                "title": f"How {topic.title()} impacts portfolios",
                "url": f"{base}/articles/{query}-portfolios",
            },
        ]

