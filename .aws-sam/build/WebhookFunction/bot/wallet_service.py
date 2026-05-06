"""High-level wallet and transaction operations."""

import hashlib

from typing import Dict, List

from bot.utils.coingecko_client import CoinGeckoClient
from bot.wallet.waaias_client import WAIaaSClient
from bot.wallet.x402_client import X402Client


class WalletService:
    """Unified wallet service for user-facing actions."""

    def __init__(
        self,
        waaias_client: WAIaaSClient,
        x402_client: X402Client,
        prices_client: CoinGeckoClient,
    ):
        self.waaias = waaias_client
        self.x402 = x402_client
        self.prices = prices_client

    def ensure_wallet(self, user_id: str) -> str:
        address = self.waaias.create_wallet(user_id)
        if not address:
            # Free/local fallback so the bot can run without WAIaaS.
            digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
            return f"0x{digest[:40]}"
        return address

    def get_balance_summary(self, wallet_address: str) -> Dict:
        balances = self.waaias.get_balances(wallet_address)
        if balances is None:
            # Keep menu/NL usable when external wallet API is unavailable.
            balances = {"ETH": 0.0, "USDC": 0.0}
        eth_price = self.prices.get_price("ETH") or 0.0
        usdc_price = self.prices.get_price("USDC") or 1.0
        eth_amount = balances.get("ETH", 0.0)
        usdc_amount = balances.get("USDC", 0.0)
        return {
            "ETH": eth_amount,
            "USDC": usdc_amount,
            "eth_usd": eth_amount * eth_price,
            "usdc_usd": usdc_amount * usdc_price,
            "total_usd": (eth_amount * eth_price) + (usdc_amount * usdc_price),
        }

    def get_transaction_history(self, wallet_address: str, limit: int = 10) -> List[Dict]:
        transactions = self.waaias.get_transactions(wallet_address, limit=limit)
        return transactions or []

    def send(
        self,
        wallet_address: str,
        destination_address: str,
        amount: float,
        currency: str,
    ) -> str:
        return self.x402.send_transaction(
            from_address=wallet_address,
            to_address=destination_address,
            amount=amount,
            token=currency.upper(),
        )

    def swap(
        self, wallet_address: str, from_token: str, to_token: str, amount: float
    ) -> str:
        return self.x402.swap_tokens(
            from_token=from_token.upper(),
            to_token=to_token.upper(),
            amount=amount,
            from_address=wallet_address,
        )

    def fetch_article(self, wallet_address: str, url: str) -> str:
        return self.x402.fetch_paywalled_content(url=url, from_address=wallet_address)

    def get_portfolio_summary(self, wallet_address: str) -> Dict:
        balance = self.get_balance_summary(wallet_address)
        return {
            "holdings": [
                {"asset": "ETH", "quantity": balance["ETH"], "value_usd": balance["eth_usd"]},
                {"asset": "USDC", "quantity": balance["USDC"], "value_usd": balance["usdc_usd"]},
            ],
            "total_usd": balance["total_usd"],
        }

    @staticmethod
    def build_request_link(wallet_address: str, amount: float, currency: str, memo: str) -> str:
        safe_memo = memo.replace(" ", "%20")
        return (
            f"ethereum:{wallet_address}"
            f"?value={amount}&token={currency.upper()}&memo={safe_memo}"
        )

