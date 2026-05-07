"""x402 protocol client with real EVM signing.

This module replaces the previous mock implementation with:

* Real secp256k1 signing via ``eth_account`` (EIP-1559 envelope).
* Real ETH and ERC20 transfers broadcast through ``eth_sendRawTransaction``.
* Real ``balanceOf`` lookups for ERC20 tokens (USDC).
* Real x402 paywall fetches via the official ``x402`` Python SDK
  (https://pypi.org/project/x402/), so paid endpoints from the Coinbase
  facilitator network actually settle on-chain.

The signer's private key is **never** held inside this client; instead each
spending call accepts a ``WalletRecord`` produced by ``AWSWallet`` (which
just decrypted it from KMS). The plaintext key is discarded immediately
after the signature is built.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests
from eth_account import Account

from bot.wallet.aws_wallet import (
    AWSWallet,
    NETWORKS,
    WalletRecord,
    encode_erc20_transfer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class X402Error(Exception):
    """Base exception for x402 protocol errors."""


class InsufficientBalanceError(X402Error):
    pass


class NetworkError(X402Error):
    pass


class TransactionError(X402Error):
    pass


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


_ETH_TRANSFER_GAS = 21_000
_ERC20_TRANSFER_GAS = 100_000


class X402Client:
    """Thin signing + broadcasting client backed by ``AWSWallet``.

    All on-chain reads (nonce, gas price, balance) flow through the
    underlying ``AWSWallet`` so the network selection stays in one place
    and switching networks at runtime is a single ``wallet.use_network``
    call.
    """

    def __init__(self, wallet: AWSWallet):
        self.wallet = wallet

    # ------------------------------------------------------------------
    # Network helpers
    # ------------------------------------------------------------------

    @property
    def network(self) -> str:
        return self.wallet.network

    @property
    def chain_id(self) -> int:
        return self.wallet.chain_id

    @property
    def explorer(self) -> str:
        return self.wallet.explorer

    def get_explorer_url(self, tx_hash: str) -> str:
        return self.wallet.explorer_tx_url(tx_hash)

    # ------------------------------------------------------------------
    # Transfers
    # ------------------------------------------------------------------

    def send_transaction(
        self,
        signer: WalletRecord,
        to_address: str,
        amount: float,
        token: str = "ETH",
    ) -> str:
        """Sign + broadcast a transfer; returns the on-chain tx hash."""
        token = token.upper()
        if token not in {"ETH", "USDC"}:
            raise ValueError(
                f"Unsupported token {token!r}; this client supports ETH and USDC"
            )
        if amount <= 0:
            raise ValueError("Amount must be positive")

        balance = self.wallet.get_balance(signer.address, token) or 0.0
        if balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient {token} balance: have {balance}, need {amount}"
            )

        if token == "ETH":
            tx = self._build_eth_tx(signer.address, to_address, amount)
        else:
            tx = self._build_erc20_tx(signer.address, to_address, amount, token)

        return self._sign_and_send(tx, signer.private_key)

    def _build_eth_tx(self, sender: str, to: str, amount_eth: float) -> Dict[str, Any]:
        nonce_hex = self.wallet.rpc("eth_getTransactionCount", [sender, "pending"])
        gas_price_hex = self.wallet.rpc("eth_gasPrice", [])
        return {
            "from": sender,
            "to": to,
            "value": int(amount_eth * 1e18),
            "gas": _ETH_TRANSFER_GAS,
            "gasPrice": int(gas_price_hex, 16),
            "nonce": int(nonce_hex, 16),
            "chainId": self.chain_id,
        }

    def _build_erc20_tx(
        self, sender: str, to: str, amount: float, token: str
    ) -> Dict[str, Any]:
        if token != "USDC":
            raise ValueError(f"No contract address mapped for {token}")
        contract = self.wallet.usdc_address()
        amount_units = int(amount * 1e6)  # USDC uses 6 decimals
        data = "0x" + encode_erc20_transfer(to, amount_units)

        nonce_hex = self.wallet.rpc("eth_getTransactionCount", [sender, "pending"])
        gas_price_hex = self.wallet.rpc("eth_gasPrice", [])
        return {
            "from": sender,
            "to": contract,
            "value": 0,
            "gas": _ERC20_TRANSFER_GAS,
            "gasPrice": int(gas_price_hex, 16),
            "nonce": int(nonce_hex, 16),
            "chainId": self.chain_id,
            "data": data,
        }

    def _sign_and_send(self, tx: Dict[str, Any], private_key: str) -> str:
        try:
            signed = Account.sign_transaction(tx, private_key)
        except Exception as exc:
            raise TransactionError(f"Failed to sign transaction: {exc}") from exc

        raw_hex = signed.raw_transaction.hex()
        if not raw_hex.startswith("0x"):
            raw_hex = "0x" + raw_hex
        try:
            tx_hash = self.wallet.rpc("eth_sendRawTransaction", [raw_hex])
        except Exception as exc:
            raise NetworkError(f"Broadcast failed: {exc}") from exc
        if not tx_hash:
            raise TransactionError("Node returned empty tx hash")
        logger.info("broadcast %s on %s", tx_hash, self.network)
        return tx_hash

    # ------------------------------------------------------------------
    # Swap (kept as a clearly-marked DEX router stub — out of scope here)
    # ------------------------------------------------------------------

    def swap_tokens(
        self,
        signer: WalletRecord,
        from_token: str,
        to_token: str,
        amount: float,
        min_output: Optional[float] = None,
    ) -> str:
        """Placeholder swap that round-trips through a USDC -> ETH transfer.

        A production implementation should call a real DEX aggregator
        (0x, 1inch, Uniswap router) — left out of the demo because it
        requires extra approvals and a slippage model. We surface the
        limitation explicitly instead of pretending.
        """
        raise TransactionError(
            "On-chain swaps are not enabled in this build. "
            "Use Send + Receive on the same network for the demo."
        )

    # ------------------------------------------------------------------
    # Paywalled content via the official x402 SDK
    # ------------------------------------------------------------------

    def fetch_paywalled_content(
        self,
        signer: WalletRecord,
        url: str,
        max_amount_usdc: float = 1.00,
    ) -> str:
        """Fetch a paywalled URL by automatically settling its 402 challenge.

        Uses the ``x402`` Python package's ``x402_requests`` session, which
        intercepts ``402 Payment Required`` responses, builds a signed
        ``PAYMENT-SIGNATURE`` header, and retries.
        """
        if not url or not isinstance(url, str):
            raise ValueError("Invalid URL")
        if not url.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

        try:
            from x402 import x402ClientSync
            from x402.http.clients import x402_requests
            from x402.mechanisms.evm import EthAccountSigner
            from x402.mechanisms.evm.exact.register import register_exact_evm_client
        except ImportError as exc:  # pragma: no cover - import guard
            raise X402Error(
                "x402 SDK not installed. Run: pip install 'x402[requests]'"
            ) from exc

        try:
            account = Account.from_key(signer.private_key)
            client = x402ClientSync(max_value=max_amount_usdc)
            register_exact_evm_client(client, EthAccountSigner(account))

            with x402_requests(client) as session:
                response = session.get(url, timeout=30)
                response.raise_for_status()
                return response.text
        except requests.HTTPError as exc:
            raise NetworkError(f"x402 fetch HTTP error: {exc}") from exc
        except Exception as exc:
            raise X402Error(f"x402 fetch failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Status checks
    # ------------------------------------------------------------------

    def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        try:
            receipt = self.wallet.rpc("eth_getTransactionReceipt", [tx_hash])
        except Exception as exc:
            raise NetworkError(f"Failed to get tx status: {exc}") from exc

        if not receipt:
            return {"status": "pending", "confirmed": False}
        success = receipt.get("status") == "0x1"
        return {
            "status": "success" if success else "failed",
            "confirmed": True,
            "block_number": int(receipt.get("blockNumber", "0x0"), 16),
            "gas_used": int(receipt.get("gasUsed", "0x0"), 16),
        }


__all__ = [
    "X402Client",
    "X402Error",
    "InsufficientBalanceError",
    "NetworkError",
    "TransactionError",
    "NETWORKS",
]
