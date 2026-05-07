"""Tests for AWSWallet provisioning, KMS round-trip, and balance reads."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from bot.wallet.aws_wallet import (
    AWSWallet,
    KMSConfigError,
    WalletNotFoundError,
    encode_erc20_transfer,
)


def _wallet(existing_user=None, kms_key="alias/test"):
    user_db = MagicMock()
    user_db.get_user.return_value = existing_user
    kms = MagicMock()
    kms.encrypt.return_value = {"CiphertextBlob": b"\x01\x02\x03"}
    kms.decrypt.return_value = {"Plaintext": bytes(32)}
    return AWSWallet(
        user_db=user_db,
        kms_key_id=kms_key,
        network="base-sepolia",
        kms_client=kms,
    )


class TestProvisioning:
    def test_creates_wallet_when_user_missing(self):
        w = _wallet(existing_user=None)
        addr = w.ensure_wallet("user-1")

        assert addr.startswith("0x") and len(addr) == 42
        # KMS encrypt was called with EncryptionContext
        w._kms.encrypt.assert_called_once()
        ec = w._kms.encrypt.call_args.kwargs["EncryptionContext"]
        assert ec == {"user_id": "user-1", "purpose": "agent-wallet"}
        # User row was upserted
        w.user_db.create_user.assert_called_once()
        w.user_db.update_user.assert_called_once()

    def test_returns_existing_address(self):
        w = _wallet(existing_user={
            "wallet_address": "0xabc",
            "wallet_key_ciphertext": base64.b64encode(b"x").decode(),
        })
        assert w.ensure_wallet("u") == "0xabc"
        w._kms.encrypt.assert_not_called()

    def test_no_kms_key_raises(self):
        w = _wallet(existing_user=None, kms_key="")
        with pytest.raises(KMSConfigError):
            w.ensure_wallet("u")


class TestLoadWallet:
    def test_decrypts_and_returns_record(self):
        # Build a real key and round-trip it through the mocked KMS
        from eth_account import Account
        acct = Account.create()
        ciphertext = base64.b64encode(b"ct").decode()
        w = _wallet(existing_user={
            "wallet_address": acct.address,
            "wallet_key_ciphertext": ciphertext,
            "network": "base-sepolia",
        })
        w._kms.decrypt.return_value = {"Plaintext": acct.key}

        rec = w.load_wallet("u")
        assert rec.address == acct.address
        assert rec.private_key == acct.key.hex()

    def test_missing_wallet_raises(self):
        w = _wallet(existing_user=None)
        with pytest.raises(WalletNotFoundError):
            w.load_wallet("u")

    def test_no_ciphertext_raises(self):
        w = _wallet(existing_user={"wallet_address": "0xabc"})
        with pytest.raises(WalletNotFoundError):
            w.load_wallet("u")


class TestBalances:
    def test_eth_balance_parses_wei(self):
        w = _wallet(existing_user=None)
        w.rpc = MagicMock(return_value=hex(2 * 10**18))  # 2 ETH
        assert w.get_balance("0xabc", "ETH") == 2.0

    def test_usdc_balance_parses_six_decimals(self):
        w = _wallet(existing_user=None)
        # 5_000_000 = 5 USDC
        w.rpc = MagicMock(return_value=hex(5_000_000))
        assert w.get_balance("0xabc", "USDC") == 5.0

    def test_balance_returns_none_on_error(self):
        w = _wallet(existing_user=None)
        w.rpc = MagicMock(side_effect=RuntimeError("boom"))
        assert w.get_balance("0xabc", "ETH") is None


class TestERC20Encoding:
    def test_transfer_calldata(self):
        data = encode_erc20_transfer("0x" + "a" * 40, 5_000_000)
        # selector
        assert data.startswith("a9059cbb")
        # padded address (lowercase)
        assert "a" * 40 in data
        # padded uint256 amount
        assert hex(5_000_000)[2:] in data


class TestNetworkSwitch:
    def test_use_network_changes_rpc_and_chain(self):
        w = _wallet(existing_user=None)
        w.use_network("base-mainnet")
        assert w.chain_id == 8453
        assert "mainnet.base.org" in w.rpc_url

    def test_unknown_network_raises(self):
        w = _wallet(existing_user=None)
        with pytest.raises(ValueError):
            w.use_network("not-a-chain")
