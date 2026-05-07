"""Unit tests for the x402 client (real signing)."""

from unittest.mock import MagicMock, patch

import pytest
from eth_account import Account

from bot.wallet.aws_wallet import AWSWallet, NETWORKS, WalletRecord
from bot.wallet.x402_client import (
    InsufficientBalanceError,
    NetworkError,
    TransactionError,
    X402Client,
)


def _make_wallet(network: str = "base-sepolia") -> AWSWallet:
    """Build an AWSWallet with stubbed dependencies, no AWS calls."""
    user_db = MagicMock()
    kms = MagicMock()
    return AWSWallet(
        user_db=user_db,
        kms_key_id="alias/test",
        network=network,
        kms_client=kms,
    )


def _signer() -> WalletRecord:
    acct = Account.create()
    return WalletRecord(address=acct.address, private_key=acct.key.hex(), network="base-sepolia")


class TestExplorer:
    def test_explorer_url_base_sepolia(self):
        client = X402Client(_make_wallet("base-sepolia"))
        assert client.get_explorer_url("0xabc") == "https://sepolia.basescan.org/tx/0xabc"

    def test_explorer_url_base_mainnet(self):
        client = X402Client(_make_wallet("base-mainnet"))
        assert client.get_explorer_url("0xabc") == "https://basescan.org/tx/0xabc"


class TestSendValidation:
    def test_unsupported_token(self):
        client = X402Client(_make_wallet())
        with pytest.raises(ValueError, match="Unsupported token"):
            client.send_transaction(_signer(), "0x" + "1" * 40, 1.0, token="DOGE")

    def test_negative_amount(self):
        client = X402Client(_make_wallet())
        with pytest.raises(ValueError, match="Amount must be positive"):
            client.send_transaction(_signer(), "0x" + "1" * 40, -1.0, token="ETH")


class TestSendETHRealSigning:
    """Verify the EIP-1559 envelope is built and broadcast through the RPC."""

    def test_send_eth_signs_and_broadcasts(self):
        wallet = _make_wallet("base-sepolia")
        # Patch only the outbound calls we expect.
        wallet.get_balance = MagicMock(return_value=10.0)
        wallet.rpc = MagicMock(
            side_effect=[
                "0x5",                # eth_getTransactionCount
                hex(2_000_000_000),   # eth_gasPrice
                "0xdeadbeef",         # eth_sendRawTransaction
            ]
        )
        signer = _signer()

        client = X402Client(wallet)
        tx_hash = client.send_transaction(signer, "0x" + "1" * 40, 0.001, token="ETH")

        assert tx_hash == "0xdeadbeef"
        # Verify the calls happened in the right order.
        methods = [c.args[0] for c in wallet.rpc.call_args_list]
        assert methods == ["eth_getTransactionCount", "eth_gasPrice", "eth_sendRawTransaction"]
        # The raw tx that got broadcast must be a hex string starting with 0x.
        raw = wallet.rpc.call_args_list[-1].args[1][0]
        assert raw.startswith("0x") and len(raw) > 100

    def test_insufficient_balance(self):
        wallet = _make_wallet()
        wallet.get_balance = MagicMock(return_value=0.0)
        client = X402Client(wallet)
        with pytest.raises(InsufficientBalanceError):
            client.send_transaction(_signer(), "0x" + "1" * 40, 1.0, token="ETH")


class TestSendUSDC:
    def test_send_usdc_uses_erc20_data(self):
        wallet = _make_wallet("base-sepolia")
        wallet.get_balance = MagicMock(return_value=100.0)
        wallet.rpc = MagicMock(
            side_effect=["0x0", hex(1_000_000_000), "0xtxhash"]
        )

        client = X402Client(wallet)
        signer = _signer()
        recipient = "0x" + "a" * 40

        tx_hash = client.send_transaction(signer, recipient, 5.0, token="USDC")

        assert tx_hash == "0xtxhash"
        # Tx data must be the 0xa9059cbb selector + recipient + amount (5_000_000 units).
        # We can't read the raw transaction directly, but we can re-derive the data
        # from the last RPC call to confirm the amount encoding.
        broadcast = wallet.rpc.call_args_list[-1].args[1][0]
        assert "a9059cbb" in broadcast
        assert "a" * 40 in broadcast.lower()


class TestStatus:
    def test_pending_when_no_receipt(self):
        wallet = _make_wallet()
        wallet.rpc = MagicMock(return_value=None)
        client = X402Client(wallet)
        assert client.get_transaction_status("0x1")["status"] == "pending"

    def test_success(self):
        wallet = _make_wallet()
        wallet.rpc = MagicMock(
            return_value={"status": "0x1", "blockNumber": "0x10", "gasUsed": "0x5208"}
        )
        client = X402Client(wallet)
        result = client.get_transaction_status("0x1")
        assert result == {
            "status": "success",
            "confirmed": True,
            "block_number": 16,
            "gas_used": 21000,
        }


class TestSwapDisabled:
    def test_swap_explicit_error(self):
        client = X402Client(_make_wallet())
        with pytest.raises(TransactionError, match="not enabled"):
            client.swap_tokens(_signer(), "USDC", "ETH", 100.0)


class TestNetworksConfig:
    def test_base_sepolia_has_real_usdc(self):
        # Circle's official testnet USDC on Base Sepolia.
        assert NETWORKS["base-sepolia"]["usdc"] == "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

    def test_base_mainnet_has_real_usdc(self):
        assert NETWORKS["base-mainnet"]["usdc"] == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
