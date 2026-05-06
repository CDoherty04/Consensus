"""Price alert business logic."""

from typing import Dict, List, Optional

from bot.db.alerts import AlertsDB
from bot.utils.coingecko_client import CoinGeckoClient
from bot.utils.validation import validate_alert_direction, validate_asset_symbol


class AlertsService:
    """Wrap DB and pricing client for alerts."""

    def __init__(self, db: AlertsDB, prices: CoinGeckoClient):
        self.db = db
        self.prices = prices

    def create_alert(
        self, user_id: str, asset_symbol: str, target_price: float, direction: str
    ) -> str:
        asset_symbol = asset_symbol.upper().strip()
        direction = direction.lower().strip()
        asset_valid, asset_error = validate_asset_symbol(asset_symbol)
        if not asset_valid:
            raise ValueError(asset_error or "Invalid asset symbol.")
        direction_valid, direction_error = validate_alert_direction(direction)
        if not direction_valid:
            raise ValueError(direction_error or "Invalid direction.")
        if target_price <= 0:
            raise ValueError("Target price must be positive.")
        return self.db.create_alert(user_id, asset_symbol, float(target_price), direction)

    def list_alerts(self, user_id: str) -> List[Dict]:
        return self.db.get_alerts(user_id)

    def delete_alert(self, user_id: str, alert_id: str) -> None:
        self.db.delete_alert(alert_id, user_id=user_id)

    def market_snapshot(self, assets: List[str]) -> List[Dict[str, Optional[float]]]:
        snapshot = []
        for asset in assets:
            symbol = asset.upper().strip()
            price, change = self.prices.get_price_and_change(symbol)
            if price is None and change is None:
                continue
            snapshot.append({"asset": symbol, "price": price, "change_24h": change})
        return snapshot

