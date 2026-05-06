"""
Unit tests for CoinGecko API client.
"""

import time
from unittest.mock import Mock, patch
import pytest
from bot.utils.coingecko_client import CoinGeckoClient, ASSET_ID_MAP, CACHE_DURATION


class TestCoinGeckoClient:
    """Tests for CoinGeckoClient initialization and basic functionality."""
    
    def test_initialization_without_api_key(self):
        """Test client initialization without API key."""
        client = CoinGeckoClient()
        assert client.api_key is None
        assert client.base_url == "https://api.coingecko.com/api/v3"
        assert client.price_cache == {}
        assert client.change_cache == {}
    
    def test_initialization_with_api_key(self):
        """Test client initialization with API key."""
        api_key = "test_api_key_123"
        client = CoinGeckoClient(api_key=api_key)
        assert client.api_key == api_key
    
    def test_get_coingecko_id_valid_symbols(self):
        """Test getting CoinGecko IDs for valid symbols."""
        client = CoinGeckoClient()
        
        assert client._get_coingecko_id('BTC') == 'bitcoin'
        assert client._get_coingecko_id('ETH') == 'ethereum'
        assert client._get_coingecko_id('SOL') == 'solana'
        assert client._get_coingecko_id('USDC') == 'usd-coin'
    
    def test_get_coingecko_id_case_insensitive(self):
        """Test that symbol lookup is case-insensitive."""
        client = CoinGeckoClient()
        
        assert client._get_coingecko_id('btc') == 'bitcoin'
        assert client._get_coingecko_id('Eth') == 'ethereum'
        assert client._get_coingecko_id('SOL') == 'solana'
    
    def test_get_coingecko_id_invalid_symbol(self):
        """Test getting CoinGecko ID for invalid symbol."""
        client = CoinGeckoClient()
        
        assert client._get_coingecko_id('INVALID') is None
        assert client._get_coingecko_id('XYZ') is None
    
    def test_is_cache_valid_fresh(self):
        """Test cache validity check for fresh data."""
        client = CoinGeckoClient()
        
        current_time = time.time()
        assert client._is_cache_valid(current_time) is True
    
    def test_is_cache_valid_expired(self):
        """Test cache validity check for expired data."""
        client = CoinGeckoClient()
        
        old_time = time.time() - CACHE_DURATION - 1
        assert client._is_cache_valid(old_time) is False
    
    def test_is_cache_valid_boundary(self):
        """Test cache validity at the boundary."""
        client = CoinGeckoClient()
        
        boundary_time = time.time() - CACHE_DURATION + 1
        assert client._is_cache_valid(boundary_time) is True


class TestGetPrice:
    """Tests for get_price method."""
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_price_success(self, mock_get):
        """Test successful price fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'bitcoin': {'usd': 45000.50}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = CoinGeckoClient()
        price = client.get_price('BTC')
        
        assert price == 45000.50
        assert 'BTC' in client.price_cache
        mock_get.assert_called_once()
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_price_with_api_key(self, mock_get):
        """Test price fetch with API key."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'ethereum': {'usd': 3000.25}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = CoinGeckoClient(api_key='test_key')
        price = client.get_price('ETH')
        
        assert price == 3000.25
        # Check that API key was included in headers
        call_kwargs = mock_get.call_args[1]
        assert 'headers' in call_kwargs
        assert call_kwargs['headers']['x-cg-pro-api-key'] == 'test_key'
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_price_cached(self, mock_get):
        """Test that cached price is returned without API call."""
        client = CoinGeckoClient()
        
        # Manually populate cache
        client.price_cache['BTC'] = (45000.50, time.time())
        
        price = client.get_price('BTC')
        
        assert price == 45000.50
        # Should not make API call
        mock_get.assert_not_called()
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_price_cache_expired(self, mock_get):
        """Test that expired cache triggers new API call."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'bitcoin': {'usd': 46000.00}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = CoinGeckoClient()
        
        # Populate cache with expired data
        old_time = time.time() - CACHE_DURATION - 1
        client.price_cache['BTC'] = (45000.50, old_time)
        
        price = client.get_price('BTC')
        
        assert price == 46000.00
        # Should make API call
        mock_get.assert_called_once()
    
    def test_get_price_invalid_symbol(self):
        """Test price fetch with invalid symbol."""
        client = CoinGeckoClient()
        price = client.get_price('INVALID')
        
        assert price is None
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_price_api_error(self, mock_get):
        """Test price fetch when API returns error."""
        mock_get.side_effect = Exception("API Error")
        
        client = CoinGeckoClient()
        price = client.get_price('BTC')
        
        assert price is None
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_price_timeout(self, mock_get):
        """Test price fetch when API times out."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        client = CoinGeckoClient()
        price = client.get_price('BTC')
        
        assert price is None
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_price_missing_data(self, mock_get):
        """Test price fetch when response is missing expected data."""
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = CoinGeckoClient()
        price = client.get_price('BTC')
        
        assert price is None


class TestGet24hChange:
    """Tests for get_24h_change method."""
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_24h_change_success(self, mock_get):
        """Test successful 24h change fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'ethereum': {'usd_24h_change': 5.5}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = CoinGeckoClient()
        change = client.get_24h_change('ETH')
        
        assert change == 5.5
        assert 'ETH' in client.change_cache
        mock_get.assert_called_once()
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_24h_change_negative(self, mock_get):
        """Test 24h change fetch with negative value."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'bitcoin': {'usd_24h_change': -2.3}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = CoinGeckoClient()
        change = client.get_24h_change('BTC')
        
        assert change == -2.3
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_24h_change_cached(self, mock_get):
        """Test that cached change is returned without API call."""
        client = CoinGeckoClient()
        
        # Manually populate cache
        client.change_cache['ETH'] = (5.5, time.time())
        
        change = client.get_24h_change('ETH')
        
        assert change == 5.5
        # Should not make API call
        mock_get.assert_not_called()
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_24h_change_cache_expired(self, mock_get):
        """Test that expired cache triggers new API call."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'ethereum': {'usd_24h_change': 6.0}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = CoinGeckoClient()
        
        # Populate cache with expired data
        old_time = time.time() - CACHE_DURATION - 1
        client.change_cache['ETH'] = (5.5, old_time)
        
        change = client.get_24h_change('ETH')
        
        assert change == 6.0
        # Should make API call
        mock_get.assert_called_once()
    
    def test_get_24h_change_invalid_symbol(self):
        """Test 24h change fetch with invalid symbol."""
        client = CoinGeckoClient()
        change = client.get_24h_change('INVALID')
        
        assert change is None
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_24h_change_api_error(self, mock_get):
        """Test 24h change fetch when API returns error."""
        mock_get.side_effect = Exception("API Error")
        
        client = CoinGeckoClient()
        change = client.get_24h_change('ETH')
        
        assert change is None


class TestGetPriceAndChange:
    """Tests for get_price_and_change method."""
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_price_and_change_success(self, mock_get):
        """Test successful fetch of both price and change."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'bitcoin': {
                'usd': 45000.50,
                'usd_24h_change': 5.5
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = CoinGeckoClient()
        price, change = client.get_price_and_change('BTC')
        
        assert price == 45000.50
        assert change == 5.5
        assert 'BTC' in client.price_cache
        assert 'BTC' in client.change_cache
        # Should only make one API call
        mock_get.assert_called_once()
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_price_and_change_both_cached(self, mock_get):
        """Test that both cached values are returned without API call."""
        client = CoinGeckoClient()
        
        # Manually populate both caches
        current_time = time.time()
        client.price_cache['BTC'] = (45000.50, current_time)
        client.change_cache['BTC'] = (5.5, current_time)
        
        price, change = client.get_price_and_change('BTC')
        
        assert price == 45000.50
        assert change == 5.5
        # Should not make API call
        mock_get.assert_not_called()
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_price_and_change_partial_cache(self, mock_get):
        """Test that API is called if only one value is cached."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'bitcoin': {
                'usd': 46000.00,
                'usd_24h_change': 6.0
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = CoinGeckoClient()
        
        # Only cache price, not change
        client.price_cache['BTC'] = (45000.50, time.time())
        
        price, change = client.get_price_and_change('BTC')
        
        assert price == 46000.00
        assert change == 6.0
        # Should make API call
        mock_get.assert_called_once()
    
    def test_get_price_and_change_invalid_symbol(self):
        """Test fetch with invalid symbol."""
        client = CoinGeckoClient()
        price, change = client.get_price_and_change('INVALID')
        
        assert price is None
        assert change is None
    
    @patch('bot.utils.coingecko_client.requests.get')
    def test_get_price_and_change_api_error(self, mock_get):
        """Test fetch when API returns error."""
        mock_get.side_effect = Exception("API Error")
        
        client = CoinGeckoClient()
        price, change = client.get_price_and_change('BTC')
        
        assert price is None
        assert change is None


class TestCacheManagement:
    """Tests for cache management methods."""
    
    def test_clear_cache(self):
        """Test clearing all cache data."""
        client = CoinGeckoClient()
        
        # Populate caches
        client.price_cache['BTC'] = (45000.50, time.time())
        client.price_cache['ETH'] = (3000.25, time.time())
        client.change_cache['BTC'] = (5.5, time.time())
        
        assert len(client.price_cache) == 2
        assert len(client.change_cache) == 1
        
        client.clear_cache()
        
        assert len(client.price_cache) == 0
        assert len(client.change_cache) == 0
    
    def test_get_cache_stats_empty(self):
        """Test cache stats when caches are empty."""
        client = CoinGeckoClient()
        
        stats = client.get_cache_stats()
        
        assert stats['price_cache_size'] == 0
        assert stats['change_cache_size'] == 0
    
    def test_get_cache_stats_populated(self):
        """Test cache stats when caches are populated."""
        client = CoinGeckoClient()
        
        # Populate caches
        client.price_cache['BTC'] = (45000.50, time.time())
        client.price_cache['ETH'] = (3000.25, time.time())
        client.change_cache['BTC'] = (5.5, time.time())
        
        stats = client.get_cache_stats()
        
        assert stats['price_cache_size'] == 2
        assert stats['change_cache_size'] == 1


class TestAssetIdMap:
    """Tests for asset ID mapping."""
    
    def test_asset_id_map_completeness(self):
        """Test that all supported assets have CoinGecko IDs."""
        required_assets = ['BTC', 'ETH', 'SOL', 'USDC', 'SPY', 'QQQ']
        
        for asset in required_assets:
            assert asset in ASSET_ID_MAP, f"Asset {asset} missing from ASSET_ID_MAP"
            assert ASSET_ID_MAP[asset] is not None
            assert isinstance(ASSET_ID_MAP[asset], str)
            assert len(ASSET_ID_MAP[asset]) > 0
