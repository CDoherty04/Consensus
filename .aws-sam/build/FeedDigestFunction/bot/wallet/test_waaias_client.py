"""
Unit tests for WAIaaS client.

Tests wallet creation, balance fetching, transaction history retrieval,
and retry logic with exponential backoff.
"""

import time
from unittest.mock import Mock, patch, MagicMock
import pytest
import requests

from bot.wallet.waaias_client import WAIaaSClient


class TestWAIaaSClient:
    """Test suite for WAIaaSClient."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test-api-key"
        self.client = WAIaaSClient(api_key=self.api_key)
    
    def test_init(self):
        """Test client initialization."""
        assert self.client.api_key == self.api_key
        assert self.client.base_url == "https://api.waaias.com/v1"
        assert self.client.max_retries == 3
        assert self.client.initial_backoff == 1.0
    
    def test_init_custom_base_url(self):
        """Test client initialization with custom base URL."""
        custom_url = "https://custom.api.com/v2"
        client = WAIaaSClient(api_key=self.api_key, base_url=custom_url)
        assert client.base_url == custom_url
    
    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base URL."""
        client = WAIaaSClient(api_key=self.api_key, base_url="https://api.com/")
        assert client.base_url == "https://api.com"
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_create_wallet_success(self, mock_request):
        """Test successful wallet creation."""
        mock_response = Mock()
        mock_response.json.return_value = {'address': '0xabc123def456'}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        address = self.client.create_wallet("123456789")
        
        assert address == '0xabc123def456'
        mock_request.assert_called_once()
        
        # Verify request parameters
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert '/wallets' in call_args[1]['url']
        assert call_args[1]['json']['user_id'] == "123456789"
        assert call_args[1]['json']['blockchain'] == 'base'
        assert call_args[1]['headers']['Authorization'] == f'Bearer {self.api_key}'
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_create_wallet_missing_address(self, mock_request):
        """Test wallet creation with missing address in response."""
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'success'}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        address = self.client.create_wallet("123456789")
        
        assert address is None
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_get_balance_eth_success(self, mock_request):
        """Test successful ETH balance fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {'balance': 1.5}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        balance = self.client.get_balance("0xabc123", "ETH")
        
        assert balance == 1.5
        
        # Verify request parameters
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'GET'
        assert '/balances' in call_args[1]['url']
        assert call_args[1]['params']['address'] == "0xabc123"
        assert call_args[1]['params']['token'] == 'ETH'
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_get_balance_usdc_success(self, mock_request):
        """Test successful USDC balance fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {'balance': 100.0}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        balance = self.client.get_balance("0xabc123", "USDC")
        
        assert balance == 100.0
        assert mock_request.call_args[1]['params']['token'] == 'USDC'
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_get_balance_case_insensitive(self, mock_request):
        """Test that token symbol is case-insensitive."""
        mock_response = Mock()
        mock_response.json.return_value = {'balance': 1.5}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        balance = self.client.get_balance("0xabc123", "eth")
        
        assert balance == 1.5
        assert mock_request.call_args[1]['params']['token'] == 'ETH'
    
    def test_get_balance_unsupported_token(self):
        """Test balance fetch with unsupported token."""
        balance = self.client.get_balance("0xabc123", "BTC")
        assert balance is None
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_get_balance_missing_balance_field(self, mock_request):
        """Test balance fetch with missing balance field in response."""
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'success'}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        balance = self.client.get_balance("0xabc123", "ETH")
        
        assert balance is None
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_get_balance_invalid_balance_value(self, mock_request):
        """Test balance fetch with non-numeric balance value."""
        mock_response = Mock()
        mock_response.json.return_value = {'balance': 'invalid'}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        balance = self.client.get_balance("0xabc123", "ETH")
        
        assert balance is None
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_get_transactions_success(self, mock_request):
        """Test successful transaction history fetch."""
        mock_transactions = [
            {
                'hash': '0xtx1',
                'from': '0xabc',
                'to': '0xdef',
                'amount': 1.5,
                'token': 'ETH',
                'timestamp': 1704067200,
                'type': 'send',
                'status': 'confirmed'
            },
            {
                'hash': '0xtx2',
                'from': '0xghi',
                'to': '0xabc',
                'amount': 100.0,
                'token': 'USDC',
                'timestamp': 1704000000,
                'type': 'receive',
                'status': 'confirmed'
            }
        ]
        
        mock_response = Mock()
        mock_response.json.return_value = {'transactions': mock_transactions}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        transactions = self.client.get_transactions("0xabc123", limit=10)
        
        assert transactions == mock_transactions
        assert len(transactions) == 2
        
        # Verify request parameters
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'GET'
        assert '/transactions' in call_args[1]['url']
        assert call_args[1]['params']['address'] == "0xabc123"
        assert call_args[1]['params']['limit'] == 10
        assert call_args[1]['params']['offset'] == 0
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_get_transactions_with_pagination(self, mock_request):
        """Test transaction history fetch with pagination parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {'transactions': []}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        self.client.get_transactions("0xabc123", limit=5, offset=10)
        
        call_args = mock_request.call_args
        assert call_args[1]['params']['limit'] == 5
        assert call_args[1]['params']['offset'] == 10
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_get_transactions_missing_field(self, mock_request):
        """Test transaction history fetch with missing transactions field."""
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'success'}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        transactions = self.client.get_transactions("0xabc123")
        
        assert transactions is None
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_get_transactions_invalid_type(self, mock_request):
        """Test transaction history fetch with non-list transactions field."""
        mock_response = Mock()
        mock_response.json.return_value = {'transactions': 'invalid'}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        transactions = self.client.get_transactions("0xabc123")
        
        assert transactions is None
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_get_balances_success(self, mock_request):
        """Test fetching all balances at once."""
        # Mock two successful responses
        mock_response_eth = Mock()
        mock_response_eth.json.return_value = {'balance': 1.5}
        mock_response_eth.raise_for_status = Mock()
        
        mock_response_usdc = Mock()
        mock_response_usdc.json.return_value = {'balance': 100.0}
        mock_response_usdc.raise_for_status = Mock()
        
        mock_request.side_effect = [mock_response_eth, mock_response_usdc]
        
        balances = self.client.get_balances("0xabc123")
        
        assert balances == {'ETH': 1.5, 'USDC': 100.0}
        assert mock_request.call_count == 2
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_get_balances_partial_failure(self, mock_request):
        """Test fetching balances when one request fails."""
        # Mock one success and one failure
        mock_response_eth = Mock()
        mock_response_eth.json.return_value = {'balance': 1.5}
        mock_response_eth.raise_for_status = Mock()
        
        mock_response_usdc = Mock()
        mock_response_usdc.raise_for_status.side_effect = requests.exceptions.Timeout()
        
        mock_request.side_effect = [mock_response_eth] + [mock_response_usdc] * 3
        
        balances = self.client.get_balances("0xabc123")
        
        # Should return partial results with 0.0 for failed request
        assert balances == {'ETH': 1.5, 'USDC': 0.0}
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_get_balances_complete_failure(self, mock_request):
        """Test fetching balances when both requests fail."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.Timeout()
        mock_request.return_value = mock_response
        
        balances = self.client.get_balances("0xabc123")
        
        assert balances is None
    
    @patch('bot.wallet.waaias_client.requests.request')
    @patch('bot.wallet.waaias_client.time.sleep')
    def test_retry_on_timeout(self, mock_sleep, mock_request):
        """Test retry logic with exponential backoff on timeout."""
        # First two attempts timeout, third succeeds
        mock_response_timeout = Mock()
        mock_response_timeout.raise_for_status.side_effect = requests.exceptions.Timeout()
        
        mock_response_success = Mock()
        mock_response_success.json.return_value = {'balance': 1.5}
        mock_response_success.raise_for_status = Mock()
        
        mock_request.side_effect = [
            mock_response_timeout,
            mock_response_timeout,
            mock_response_success
        ]
        
        balance = self.client.get_balance("0xabc123", "ETH")
        
        assert balance == 1.5
        assert mock_request.call_count == 3
        
        # Verify exponential backoff: 1s, 2s
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list[0][0][0] == 1.0
        assert mock_sleep.call_args_list[1][0][0] == 2.0
    
    @patch('bot.wallet.waaias_client.requests.request')
    @patch('bot.wallet.waaias_client.time.sleep')
    def test_retry_exhausted(self, mock_sleep, mock_request):
        """Test that retries are exhausted after max attempts."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.Timeout()
        mock_request.return_value = mock_response
        
        balance = self.client.get_balance("0xabc123", "ETH")
        
        assert balance is None
        assert mock_request.call_count == 3  # max_retries
        assert mock_sleep.call_count == 2  # No sleep after last attempt
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_no_retry_on_client_error(self, mock_request):
        """Test that 4xx errors are not retried."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_request.return_value = mock_response
        
        balance = self.client.get_balance("0xabc123", "ETH")
        
        assert balance is None
        assert mock_request.call_count == 1  # No retries
    
    @patch('bot.wallet.waaias_client.requests.request')
    @patch('bot.wallet.waaias_client.time.sleep')
    def test_retry_on_server_error(self, mock_sleep, mock_request):
        """Test that 5xx errors are retried."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_request.return_value = mock_response
        
        balance = self.client.get_balance("0xabc123", "ETH")
        
        assert balance is None
        assert mock_request.call_count == 3  # Retried
        assert mock_sleep.call_count == 2
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_unexpected_exception(self, mock_request):
        """Test handling of unexpected exceptions."""
        mock_request.side_effect = ValueError("Unexpected error")
        
        balance = self.client.get_balance("0xabc123", "ETH")
        
        assert balance is None
        assert mock_request.call_count == 1  # No retries on unexpected errors
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_request_headers(self, mock_request):
        """Test that correct headers are sent with requests."""
        mock_response = Mock()
        mock_response.json.return_value = {'balance': 1.5}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        self.client.get_balance("0xabc123", "ETH")
        
        call_args = mock_request.call_args
        headers = call_args[1]['headers']
        
        assert headers['Authorization'] == f'Bearer {self.api_key}'
        assert headers['Content-Type'] == 'application/json'
    
    @patch('bot.wallet.waaias_client.requests.request')
    def test_request_timeout(self, mock_request):
        """Test that requests have appropriate timeout."""
        mock_response = Mock()
        mock_response.json.return_value = {'balance': 1.5}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        self.client.get_balance("0xabc123", "ETH")
        
        call_args = mock_request.call_args
        assert call_args[1]['timeout'] == 30


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
