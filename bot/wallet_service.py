"""High-level wallet and transaction operations.

Backed by ``AWSWallet`` (KMS-encrypted keys in DynamoDB) and ``X402Client``
(real on-chain signing + x402 paywall settlement).
"""

from __future__ import annotations

from typing import Dict, List

from bot.utils.coingecko_client import CoinGeckoClient
from bot.wallet.aws_wallet import AWSWallet
from bot.wallet.x402_client import X402Client


class WalletService:
    """Unified wallet service for user-facing actions."""

    def __init__(
        self,
        aws_wallet: AWSWallet,
        x402_client: X402Client,
        prices_client: CoinGeckoClient,
    ):
        self.wallet = aws_wallet
        self.x402 = x402_client
        self.prices = prices_client

    # ------------------------------------------------------------------
    # Provisioning
    # ------------------------------------------------------------------

    def ensure_wallet(self, user_id: str) -> str:
        """Provision a fresh KMS-backed wallet for the user if needed."""
        return self.wallet.ensure_wallet(user_id)

    def use_network(self, network: str) -> None:
        self.wallet.use_network(network)

    # ------------------------------------------------------------------
    # Read APIs
    # ------------------------------------------------------------------

    def get_balance_summary(self, wallet_address: str) -> Dict:
        balances = self.wallet.get_balances(wallet_address) or {"ETH": 0.0, "USDC": 0.0}
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
        return self.wallet.get_transactions(wallet_address, limit=limit) or []

    def get_portfolio_summary(self, wallet_address: str) -> Dict:
        balance = self.get_balance_summary(wallet_address)
        return {
            "holdings": [
                {"asset": "ETH", "quantity": balance["ETH"], "value_usd": balance["eth_usd"]},
                {"asset": "USDC", "quantity": balance["USDC"], "value_usd": balance["usdc_usd"]},
            ],
            "total_usd": balance["total_usd"],
        }

    # ------------------------------------------------------------------
    # Spending APIs (require user_id so we can decrypt their key)
    # ------------------------------------------------------------------

    def send(
        self,
        user_id: str,
        destination_address: str,
        amount: float,
        currency: str,
    ) -> str:
        signer = self.wallet.load_wallet(user_id)
        try:
            return self.x402.send_transaction(
                signer=signer,
                to_address=destination_address,
                amount=amount,
                token=currency.upper(),
            )
        finally:
            # Best-effort scrub of the in-memory key reference
            signer.private_key = ""

    def swap(
        self, user_id: str, from_token: str, to_token: str, amount: float
    ) -> str:
        signer = self.wallet.load_wallet(user_id)
        try:
            return self.x402.swap_tokens(
                signer=signer,
                from_token=from_token.upper(),
                to_token=to_token.upper(),
                amount=amount,
            )
        finally:
            signer.private_key = ""

    def fetch_article(self, user_id: str, url: str, max_amount_usdc: float = 1.00) -> str:
        signer = self.wallet.load_wallet(user_id)
        try:
            return self.x402.fetch_paywalled_content(
                signer=signer, url=url, max_amount_usdc=max_amount_usdc
            )
        finally:
            signer.private_key = ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def build_request_link(wallet_address: str, amount: float, currency: str, memo: str) -> str:
        """Build an EIP-681 payment request URI."""
        currency = currency.upper()
        if currency == "ETH":
            value_wei = int(amount * 1e18)
            return f"ethereum:{wallet_address}@8453?value={value_wei}"
        # USDC on Base mainnet by default
        usdc = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        value_units = int(amount * 1e6)
        return (
            f"ethereum:{usdc}@8453/transfer"
            f"?address={wallet_address}&uint256={value_units}"
        )
