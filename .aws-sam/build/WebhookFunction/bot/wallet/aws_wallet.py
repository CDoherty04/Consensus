"""AWS-native non-custodial wallet.

Generates real EVM (secp256k1) keypairs with ``eth_account``, encrypts the
private key under an AWS KMS customer managed key, and persists the
ciphertext + address on the user record in DynamoDB. All on-chain reads
(balances, tx history, nonce, gas) go to a Base / Base Sepolia JSON-RPC
endpoint.

This is the real wallet that backs ``WalletService`` and ``X402Client`` —
it replaces the previous mocked WAIaaS HTTP client.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import boto3
import requests
from botocore.exceptions import ClientError
from eth_account import Account

# Enable HD-style mnemonic features lazily; not strictly required.
Account.enable_unaudited_hdwallet_features()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Network / token configuration
# ---------------------------------------------------------------------------

NETWORKS: Dict[str, Dict[str, object]] = {
    "base-mainnet": {
        "rpc_url": "https://mainnet.base.org",
        "chain_id": 8453,
        "explorer": "https://basescan.org",
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    },
    "base-sepolia": {
        "rpc_url": "https://sepolia.base.org",
        "chain_id": 84532,
        "explorer": "https://sepolia.basescan.org",
        # Circle's official testnet USDC on Base Sepolia
        "usdc": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    },
    "optimism": {
        "rpc_url": "https://mainnet.optimism.io",
        "chain_id": 10,
        "explorer": "https://optimistic.etherscan.io",
        "usdc": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
    },
}

# ERC20 selectors
_BALANCE_OF = "0x70a08231"
_TRANSFER = "0xa9059cbb"
_DECIMALS = "0x313ce567"


class WalletError(Exception):
    """Base exception for wallet operations."""


class WalletNotFoundError(WalletError):
    """Raised when no wallet exists for a given user."""


class KMSConfigError(WalletError):
    """Raised when AWS KMS is not configured for key wrapping."""


@dataclass
class WalletRecord:
    """In-memory representation of a user's wallet."""

    address: str
    private_key: str
    network: str


# ---------------------------------------------------------------------------
# AWSWallet
# ---------------------------------------------------------------------------


class AWSWallet:
    """Non-custodial-on-AWS wallet manager.

    The user's secp256k1 private key is generated on the Lambda, immediately
    encrypted under a KMS CMK, and the ciphertext is stored on the user's
    DynamoDB item. Plaintext keys never leave Lambda memory and are never
    written to logs or DynamoDB.

    A single ``AWSWallet`` instance is reused across invocations (warm
    Lambdas) and is safe to share between users — every method requires the
    ``user_id`` so we can fetch the right ciphertext.
    """

    def __init__(
        self,
        user_db,  # bot.db.user_state.UserStateDB (avoid hard dep / cycle)
        kms_key_id: Optional[str] = None,
        network: str = "base-sepolia",
        kms_client=None,
        rpc_session: Optional[requests.Session] = None,
    ) -> None:
        if network not in NETWORKS:
            raise ValueError(
                f"Unsupported network {network!r}; pick one of {list(NETWORKS)}"
            )

        self.user_db = user_db
        self.kms_key_id = kms_key_id or os.getenv("WALLET_KMS_KEY_ID") or ""
        self.network = network
        self._cfg = NETWORKS[network]
        self._kms = kms_client or boto3.client(
            "kms", region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        self._http = rpc_session or requests.Session()

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def use_network(self, network: str) -> None:
        """Switch RPC endpoint / chain id (used when user picks a network)."""
        if network not in NETWORKS:
            raise ValueError(f"Unsupported network {network!r}")
        self.network = network
        self._cfg = NETWORKS[network]

    @property
    def rpc_url(self) -> str:
        return str(self._cfg["rpc_url"])

    @property
    def chain_id(self) -> int:
        return int(self._cfg["chain_id"])

    @property
    def explorer(self) -> str:
        return str(self._cfg["explorer"])

    def usdc_address(self) -> str:
        return str(self._cfg["usdc"])

    def explorer_tx_url(self, tx_hash: str) -> str:
        return f"{self.explorer}/tx/{tx_hash}"

    # ------------------------------------------------------------------
    # Wallet provisioning
    # ------------------------------------------------------------------

    def ensure_wallet(self, user_id: str) -> str:
        """Return the user's wallet address, creating one if needed.

        Steps for new users:
            1. ``eth_account.Account.create()`` generates a fresh secp256k1 key.
            2. The private key is encrypted under the KMS CMK
               (``Encrypt`` API, AES-256 envelope) — we never persist or
               return the plaintext.
            3. ``address`` and base64 ``key_ciphertext`` are written to the
               user's DynamoDB item.
        """
        existing = self.user_db.get_user(user_id) or {}
        addr = existing.get("wallet_address")
        if addr and existing.get("wallet_key_ciphertext"):
            return addr

        if not self.kms_key_id:
            raise KMSConfigError(
                "WALLET_KMS_KEY_ID is not set; cannot create a wallet "
                "without an AWS KMS key to encrypt the private key."
            )

        acct = Account.create()
        ciphertext_b64 = self._kms_encrypt(acct.key, user_id)

        updates = {
            "wallet_address": acct.address,
            "wallet_key_ciphertext": ciphertext_b64,
            "wallet_kms_key_id": self.kms_key_id,
            "wallet_created_at": int(time.time()),
        }
        if existing:
            self.user_db.update_user(user_id, updates)
        else:
            # Create user with the address; supplemental fields go via update.
            self.user_db.create_user(user_id=user_id, wallet_address=acct.address)
            self.user_db.update_user(
                user_id,
                {
                    "wallet_key_ciphertext": ciphertext_b64,
                    "wallet_kms_key_id": self.kms_key_id,
                    "wallet_created_at": updates["wallet_created_at"],
                },
            )

        logger.info("Provisioned wallet %s for user %s", acct.address, user_id)
        return acct.address

    def load_wallet(self, user_id: str) -> WalletRecord:
        """Fetch + decrypt the user's wallet for signing.

        The plaintext key is held only on the returned ``WalletRecord`` and
        should be discarded by the caller as soon as the signature is built.
        """
        user = self.user_db.get_user(user_id)
        if not user or not user.get("wallet_address"):
            raise WalletNotFoundError(f"No wallet for user {user_id}")

        ciphertext_b64 = user.get("wallet_key_ciphertext")
        if not ciphertext_b64:
            raise WalletNotFoundError(
                f"User {user_id} has wallet_address but no encrypted key; "
                "wallet was provisioned outside AWS KMS and cannot sign."
            )

        plaintext = self._kms_decrypt(ciphertext_b64, user_id)
        # eth_account expects a 0x-prefixed hex string or bytes
        return WalletRecord(
            address=user["wallet_address"],
            private_key=plaintext.hex() if isinstance(plaintext, (bytes, bytearray)) else plaintext,
            network=user.get("network", self.network),
        )

    # ------------------------------------------------------------------
    # Read-only on-chain queries
    # ------------------------------------------------------------------

    def get_balance(self, address: str, token: str = "ETH") -> Optional[float]:
        """Return on-chain balance for ETH or USDC. Returns ``None`` on error."""
        token = token.upper()
        try:
            if token == "ETH":
                wei_hex = self._rpc("eth_getBalance", [address, "latest"])
                return int(wei_hex, 16) / 1e18

            if token == "USDC":
                contract = self.usdc_address()
                data = _BALANCE_OF + _pad_address(address)
                raw = self._rpc(
                    "eth_call",
                    [{"to": contract, "data": data}, "latest"],
                )
                if not raw or raw == "0x":
                    return 0.0
                # USDC = 6 decimals
                return int(raw, 16) / 1e6

            logger.warning("Unsupported token for balance: %s", token)
            return None
        except Exception as exc:  # pragma: no cover - network errors
            logger.warning("balance query failed for %s/%s: %s", address, token, exc)
            return None

    def get_balances(self, address: str) -> Optional[Dict[str, float]]:
        eth = self.get_balance(address, "ETH")
        usdc = self.get_balance(address, "USDC")
        if eth is None and usdc is None:
            return None
        return {"ETH": eth or 0.0, "USDC": usdc or 0.0}

    def get_transactions(
        self, address: str, limit: int = 10, offset: int = 0
    ) -> Optional[List[Dict]]:
        """Best-effort tx history via Basescan-style explorer API.

        Falls back to an empty list (rather than ``None``) so the bot UI
        always renders a "no transactions yet" panel rather than an error.
        """
        # The public mainnet/sepolia.basescan.org API doesn't require a key
        # for low-volume reads. We use it opportunistically.
        api_root = self.explorer.replace("//", "//api.") + "/api"
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "page": str(offset // limit + 1),
            "offset": str(limit),
            "sort": "desc",
        }
        try:
            r = self._http.get(api_root, params=params, timeout=15)
            r.raise_for_status()
            payload = r.json()
            if str(payload.get("status")) != "1":
                return []
            txs: List[Dict] = []
            for raw in payload.get("result", [])[:limit]:
                txs.append(
                    {
                        "hash": raw.get("hash"),
                        "from": raw.get("from"),
                        "to": raw.get("to"),
                        "amount": int(raw.get("value", "0")) / 1e18,
                        "token": "ETH",
                        "timestamp": int(raw.get("timeStamp", "0")),
                        "type": "send"
                        if (raw.get("from", "").lower() == address.lower())
                        else "receive",
                        "status": "confirmed" if raw.get("isError") == "0" else "failed",
                    }
                )
            return txs
        except Exception as exc:
            logger.info("explorer tx history unavailable: %s", exc)
            return []

    # ------------------------------------------------------------------
    # JSON-RPC primitives
    # ------------------------------------------------------------------

    def rpc(self, method: str, params: list):
        """Public RPC bridge so ``X402Client`` can share the same endpoint."""
        return self._rpc(method, params)

    def _rpc(self, method: str, params: list):
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        r = self._http.post(self.rpc_url, json=payload, timeout=20)
        r.raise_for_status()
        body = r.json()
        if body.get("error"):
            raise WalletError(f"RPC {method} failed: {body['error']}")
        return body.get("result")

    # ------------------------------------------------------------------
    # KMS envelope encryption
    # ------------------------------------------------------------------

    def _kms_encrypt(self, plaintext: bytes, user_id: str) -> str:
        try:
            resp = self._kms.encrypt(
                KeyId=self.kms_key_id,
                Plaintext=plaintext,
                EncryptionContext={"user_id": user_id, "purpose": "agent-wallet"},
            )
        except ClientError as exc:  # pragma: no cover - aws errors
            raise WalletError(f"KMS encrypt failed: {exc}") from exc
        return base64.b64encode(resp["CiphertextBlob"]).decode("ascii")

    def _kms_decrypt(self, ciphertext_b64: str, user_id: str) -> bytes:
        try:
            resp = self._kms.decrypt(
                CiphertextBlob=base64.b64decode(ciphertext_b64),
                EncryptionContext={"user_id": user_id, "purpose": "agent-wallet"},
            )
        except ClientError as exc:  # pragma: no cover - aws errors
            raise WalletError(f"KMS decrypt failed: {exc}") from exc
        return resp["Plaintext"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pad_address(address: str) -> str:
    """Pad a 0x-prefixed address to 32-byte ABI word (no leading 0x)."""
    return address[2:].lower().zfill(64)


def _pad_uint(value: int) -> str:
    return hex(value)[2:].zfill(64)


def encode_erc20_transfer(to_address: str, amount_units: int) -> str:
    """ABI-encode ``transfer(address,uint256)`` for a raw tx ``data`` field."""
    return _TRANSFER + _pad_address(to_address) + _pad_uint(amount_units)
