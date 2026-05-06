"""
Unit tests for x402 protocol client.

Tests cover transaction sending, token swaps, paywalled content fetching,
error handling, and network communication.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from bot.wallet.x402_client import (
    X402Client,
    X402Error,
    InsufficientBalanceError,
    NetworkError,
    TransactionError,
    NETWORKS
)


class TestX402ClientInitialization:
    """Test X402Client initialization and configuration."""
    
    def test_init_with_default_network(self):
        """Test client initialization with default network."""
        client = X402Client(private_key="0x123")
        
        assert client.private_key == "0x123"
        assert client.network == "base-mainnet"
        assert client.rpc_url == NETWORKS["base-mainnet"]["rpc_url"]
        assert client.chain_id == NETWORKS["base-mainnet"]["chain_id"]
    
    def test_init_with_custom_network(self):
        """Test client initialization with custom network."""
        client = X402Client(private_key="0x123", network="base-sepolia")
        
        assert client.network == "base-sepolia"
        assert client.rpc_url == NETWORKS["base-sepolia"]["rpc_url"]
        assert client.chain_id == NETWORKS["base-sepolia"]["chain_id"]
    
    def test_init_with_invalid_network(self):
        """Test client initialization with invalid network raises error."""
        with pytest.raises(ValueError, match="Unsupported network"):
            X402Client(private_key="0x123", network="invalid-network")


class TestSendTransaction:
    """Test send_transaction method."""
    
    @patch.object(X402Client, '_get_balance')
    @patch.object(X402Client, '_send_eth_transaction')
    def test_send_eth_transaction_success(self, mock_send_eth, mock_get_balance):
        """Test successful ETH transaction."""
        mock_get_balance.return_value = 1.0
        mock_send_eth.return_value = "0xabc123"
        
        client = X402Client(private_key="0x123")
        tx_hash = client.send_transaction(
            from_address="0xfrom",
            to_address="0xto",
            amount=0.5,
            token="ETH"
        )
        
        assert tx_hash == "0xabc123"
        mock_get_balance.assert_called_once_with("0xfrom", "ETH")
        mock_send_eth.assert_called_once_with("0xfrom", "0xto", 0.5)
    
    @patch.object(X402Client, '_get_balance')
    @patch.object(X402Client, '_send_erc20_transaction')
    def test_send_usdc_transaction_success(self, mock_send_erc20, mock_get_balance):
        """Test successful USDC transaction."""
        mock_get_balance.return_value = 100.0
        mock_send_erc20.return_value = "0xdef456"
        
        client = X402Client(private_key="0x123")
        tx_hash = client.send_transaction(
            from_address="0xfrom",
            to_address="0xto",
            amount=50.0,
            token="USDC"
        )
        
        assert tx_hash == "0xdef456"
        mock_get_balance.assert_called_once_with("0xfrom", "USDC")
        mock_send_erc20.assert_called_once_with("0xfrom", "0xto", 50.0, "USDC")
    
    @patch.object(X402Client, '_get_balance')
    def test_send_transaction_insufficient_balance(self, mock_get_balance):
        """Test transaction fails with insufficient balance."""
        mock_get_balance.return_value = 0.1
        
        client = X402Client(private_key="0x123")
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient ETH balance"):
            client.send_transaction(
                from_address="0xfrom",
                to_address="0xto",
                amount=1.0,
                token="ETH"
            )
    
    def test_send_transaction_invalid_token(self):
        """Test transaction fails with invalid token."""
        client = X402Client(private_key="0x123")
        
        with pytest.raises(ValueError, match="Unsupported token"):
            client.send_transaction(
                from_address="0xfrom",
                to_address="0xto",
                amount=1.0,
                token="INVALID"
            )
    
    def test_send_transaction_negative_amount(self):
        """Test transaction fails with negative amount."""
        client = X402Client(private_key="0x123")
        
        with pytest.raises(ValueError, match="Amount must be positive"):
            client.send_transaction(
                from_address="0xfrom",
                to_address="0xto",
                amount=-1.0,
                token="ETH"
            )
    
    def test_send_transaction_zero_amount(self):
        """Test transaction fails with zero amount."""
        client = X402Client(private_key="0x123")
        
        with pytest.raises(ValueError, match="Amount must be positive"):
            client.send_transaction(
                from_address="0xfrom",
                to_address="0xto",
                amount=0.0,
                token="ETH"
            )


class TestSwapTokens:
    """Test swap_tokens method."""
    
    @patch.object(X402Client, '_get_balance')
    @patch.object(X402Client, '_get_swap_quote')
    @patch.object(X402Client, '_execute_swap')
    def test_swap_tokens_success(self, mock_execute, mock_quote, mock_balance):
        """Test successful token swap."""
        mock_balance.return_value = 100.0
        mock_quote.return_value = 0.05
        mock_execute.return_value = "0xswap123"
        
        client = X402Client(private_key="0x123")
        tx_hash = client.swap_tokens(
            from_token="USDC",
            to_token="ETH",
            amount=100.0,
            from_address="0xfrom"
        )
        
        assert tx_hash == "0xswap123"
        mock_balance.assert_called_once_with("0xfrom", "USDC")
        mock_quote.assert_called_once_with("USDC", "ETH", 100.0)
    
    @patch.object(X402Client, '_get_balance')
    def test_swap_tokens_insufficient_balance(self, mock_balance):
        """Test swap fails with insufficient balance."""
        mock_balance.return_value = 10.0
        
        client = X402Client(private_key="0x123")
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient USDC balance"):
            client.swap_tokens(
                from_token="USDC",
                to_token="ETH",
                amount=100.0,
                from_address="0xfrom"
            )
    
    def test_swap_tokens_same_token(self):
        """Test swap fails when from and to tokens are the same."""
        client = X402Client(private_key="0x123")
        
        with pytest.raises(ValueError, match="Cannot swap token to itself"):
            client.swap_tokens(
                from_token="ETH",
                to_token="ETH",
                amount=1.0,
                from_address="0xfrom"
            )
    
    def test_swap_tokens_invalid_from_token(self):
        """Test swap fails with invalid from_token."""
        client = X402Client(private_key="0x123")
        
        with pytest.raises(ValueError, match="Unsupported from_token"):
            client.swap_tokens(
                from_token="INVALID",
                to_token="ETH",
                amount=1.0,
                from_address="0xfrom"
            )
    
    def test_swap_tokens_invalid_to_token(self):
        """Test swap fails with invalid to_token."""
        client = X402Client(private_key="0x123")
        
        with pytest.raises(ValueError, match="Unsupported to_token"):
            client.swap_tokens(
                from_token="ETH",
                to_token="INVALID",
                amount=1.0,
                from_address="0xfrom"
            )
    
    @patch.object(X402Client, '_get_balance')
    @patch.object(X402Client, '_get_swap_quote')
    def test_swap_tokens_slippage_protection(self, mock_quote, mock_balance):
        """Test swap fails when output is below minimum."""
        mock_balance.return_value = 100.0
        mock_quote.return_value = 0.01  # Low output
        
        client = X402Client(private_key="0x123")
        
        with pytest.raises(TransactionError, match="below minimum"):
            client.swap_tokens(
                from_token="USDC",
                to_token="ETH",
                amount=100.0,
                from_address="0xfrom",
                min_output=0.05  # Higher than estimated
            )


class TestFetchPaywalledContent:
    """Test fetch_paywalled_content method."""
    
    @patch.object(X402Client, '_get_payment_info')
    @patch.object(X402Client, '_get_balance')
    @patch.object(X402Client, 'send_transaction')
    @patch.object(X402Client, '_retrieve_content')
    def test_fetch_content_success(self, mock_retrieve, mock_send, mock_balance, mock_payment_info):
        """Test successful paywalled content fetch."""
        mock_payment_info.return_value = {
            'amount': 0.001,
            'token': 'ETH',
            'recipient': '0xrecipient'
        }
        mock_balance.return_value = 1.0
        mock_send.return_value = "0xtx123"
        mock_retrieve.return_value = "Article content here"
        
        client = X402Client(private_key="0x123")
        content = client.fetch_paywalled_content(
            url="https://example.com/article",
            from_address="0xfrom"
        )
        
        assert content == "Article content here"
        mock_payment_info.assert_called_once_with("https://example.com/article")
        mock_balance.assert_called_once_with("0xfrom", "ETH")
        mock_send.assert_called_once()
        mock_retrieve.assert_called_once_with("https://example.com/article", "0xtx123")
    
    def test_fetch_content_invalid_url(self):
        """Test fetch fails with invalid URL."""
        client = X402Client(private_key="0x123")
        
        with pytest.raises(ValueError, match="Invalid URL"):
            client.fetch_paywalled_content(url="", from_address="0xfrom")
        
        with pytest.raises(ValueError, match="must start with http"):
            client.fetch_paywalled_content(url="not-a-url", from_address="0xfrom")
    
    @patch.object(X402Client, '_get_payment_info')
    def test_fetch_content_no_payment_info(self, mock_payment_info):
        """Test fetch fails when payment info cannot be retrieved."""
        mock_payment_info.return_value = None
        
        client = X402Client(private_key="0x123")
        
        with pytest.raises(TransactionError, match="Failed to get payment information"):
            client.fetch_paywalled_content(
                url="https://example.com/article",
                from_address="0xfrom"
            )
    
    @patch.object(X402Client, '_get_payment_info')
    @patch.object(X402Client, '_get_balance')
    def test_fetch_content_insufficient_balance(self, mock_balance, mock_payment_info):
        """Test fetch fails with insufficient balance for micropayment."""
        mock_payment_info.return_value = {
            'amount': 0.001,
            'token': 'ETH',
            'recipient': '0xrecipient'
        }
        mock_balance.return_value = 0.0001  # Less than required
        
        client = X402Client(private_key="0x123")
        
        with pytest.raises(InsufficientBalanceError, match="Insufficient ETH balance"):
            client.fetch_paywalled_content(
                url="https://example.com/article",
                from_address="0xfrom"
            )


class TestNetworkCommunication:
    """Test network communication and error handling."""
    
    @patch('bot.wallet.x402_client.requests.post')
    def test_rpc_request_success(self, mock_post):
        """Test successful RPC request."""
        mock_response = Mock()
        mock_response.json.return_value = {'result': '0x123'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = X402Client(private_key="0x123")
        result = client._make_rpc_request('eth_blockNumber', [])
        
        assert result == '0x123'
        mock_post.assert_called_once()
    
    @patch('bot.wallet.x402_client.requests.post')
    def test_rpc_request_timeout_with_retry(self, mock_post):
        """Test RPC request retries on timeout."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()
        
        client = X402Client(private_key="0x123")
        
        with pytest.raises(NetworkError, match="timed out"):
            client._make_rpc_request('eth_blockNumber', [])
        
        # Should retry MAX_RETRIES times
        assert mock_post.call_count == 4  # Initial + 3 retries
    
    @patch('bot.wallet.x402_client.requests.post')
    def test_rpc_request_network_error(self, mock_post):
        """Test RPC request handles network errors."""
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("Network error")
        
        client = X402Client(private_key="0x123")
        
        with pytest.raises(NetworkError, match="RPC request failed"):
            client._make_rpc_request('eth_blockNumber', [])
    
    @patch('bot.wallet.x402_client.requests.post')
    def test_rpc_request_rpc_error(self, mock_post):
        """Test RPC request handles RPC errors."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'error': {'message': 'Invalid method'}
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = X402Client(private_key="0x123")
        
        with pytest.raises(NetworkError, match="RPC error"):
            client._make_rpc_request('invalid_method', [])


class TestTransactionStatus:
    """Test transaction status checking."""
    
    @patch.object(X402Client, '_make_rpc_request')
    def test_get_transaction_status_pending(self, mock_rpc):
        """Test getting status of pending transaction."""
        mock_rpc.return_value = None
        
        client = X402Client(private_key="0x123")
        status = client.get_transaction_status("0xtx123")
        
        assert status['status'] == 'pending'
        assert status['confirmed'] is False
    
    @patch.object(X402Client, '_make_rpc_request')
    def test_get_transaction_status_success(self, mock_rpc):
        """Test getting status of successful transaction."""
        mock_rpc.return_value = {
            'status': '0x1',
            'blockNumber': '0x100',
            'gasUsed': '0x5208'
        }
        
        client = X402Client(private_key="0x123")
        status = client.get_transaction_status("0xtx123")
        
        assert status['status'] == 'success'
        assert status['confirmed'] is True
        assert status['block_number'] == 256
        assert status['gas_used'] == 21000
    
    @patch.object(X402Client, '_make_rpc_request')
    def test_get_transaction_status_failed(self, mock_rpc):
        """Test getting status of failed transaction."""
        mock_rpc.return_value = {
            'status': '0x0',
            'blockNumber': '0x100',
            'gasUsed': '0x5208'
        }
        
        client = X402Client(private_key="0x123")
        status = client.get_transaction_status("0xtx123")
        
        assert status['status'] == 'failed'
        assert status['confirmed'] is True


class TestExplorerUrl:
    """Test block explorer URL generation."""
    
    def test_get_explorer_url_base_mainnet(self):
        """Test explorer URL for Base mainnet."""
        client = X402Client(private_key="0x123", network="base-mainnet")
        url = client.get_explorer_url("0xtx123")
        
        assert url == "https://basescan.org/tx/0xtx123"
    
    def test_get_explorer_url_base_sepolia(self):
        """Test explorer URL for Base Sepolia."""
        client = X402Client(private_key="0x123", network="base-sepolia")
        url = client.get_explorer_url("0xtx123")
        
        assert url == "https://sepolia.basescan.org/tx/0xtx123"


class TestSwapQuote:
    """Test swap quote calculation."""
    
    def test_get_swap_quote_usdc_to_eth(self):
        """Test swap quote from USDC to ETH."""
        client = X402Client(private_key="0x123")
        output = client._get_swap_quote("USDC", "ETH", 2000.0)
        
        # 2000 USDC / 2000 (ETH price) = 1.0 ETH
        assert output == pytest.approx(1.0, rel=0.01)
    
    def test_get_swap_quote_eth_to_usdc(self):
        """Test swap quote from ETH to USDC."""
        client = X402Client(private_key="0x123")
        output = client._get_swap_quote("ETH", "USDC", 1.0)
        
        # 1 ETH * 2000 (ETH price) = 2000 USDC
        assert output == pytest.approx(2000.0, rel=0.01)
    
    def test_get_swap_quote_btc_to_sol(self):
        """Test swap quote from BTC to SOL."""
        client = X402Client(private_key="0x123")
        output = client._get_swap_quote("BTC", "SOL", 1.0)
        
        # 1 BTC * 40000 / 100 (SOL price) = 400 SOL
        assert output == pytest.approx(400.0, rel=0.01)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
