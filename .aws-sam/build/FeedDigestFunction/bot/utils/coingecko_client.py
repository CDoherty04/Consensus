"""
CoinGecko API client for fetching cryptocurrency price data.

This module provides a client for interacting with the CoinGecko API to fetch
current asset prices and 24-hour price change percentages. It includes caching
to reduce API calls and improve performance.
"""

import time
from typing import Dict, Optional, Tuple
import requests


# Asset symbol to CoinGecko ID mapping
ASSET_ID_MAP = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'SOL': 'solana',
    'USDC': 'usd-coin',
    'SPY': 'spy',  # Note: May not be available on CoinGecko
    'QQQ': 'qqq'   # Note: May not be available on CoinGecko
}

# Cache duration in seconds (5 minutes)
CACHE_DURATION = 300


class CoinGeckoClient:
    """
    Client for interacting with the CoinGecko API.
    
    This client provides methods to fetch current asset prices and 24-hour
    price change percentages. It includes a simple in-memory cache to reduce
    API calls and improve performance.
    
    Attributes:
        api_key: Optional CoinGecko API key for authenticated requests
        base_url: Base URL for CoinGecko API
        price_cache: Cache for price data
        change_cache: Cache for 24-hour change data
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the CoinGecko client.
        
        Args:
            api_key: Optional CoinGecko API key for authenticated requests
        """
        self.api_key = api_key
        self.base_url = "https://api.coingecko.com/api/v3"
        
        # Cache structure: {asset_symbol: (value, timestamp)}
        self.price_cache: Dict[str, Tuple[float, float]] = {}
        self.change_cache: Dict[str, Tuple[float, float]] = {}
    
    def _get_coingecko_id(self, asset_symbol: str) -> Optional[str]:
        """
        Get the CoinGecko ID for an asset symbol.
        
        Args:
            asset_symbol: Asset symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            CoinGecko ID or None if not found
        """
        return ASSET_ID_MAP.get(asset_symbol.upper())
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """
        Check if a cached value is still valid.
        
        Args:
            timestamp: Timestamp when the value was cached
            
        Returns:
            True if cache is still valid, False otherwise
        """
        return (time.time() - timestamp) < CACHE_DURATION
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make a request to the CoinGecko API.
        
        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            
        Returns:
            JSON response as dictionary or None on error
        """
        url = f"{self.base_url}/{endpoint}"
        
        # Add API key to headers if provided
        headers = {}
        if self.api_key:
            headers['x-cg-pro-api-key'] = self.api_key
        
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            print(f"CoinGecko API request timed out: {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"CoinGecko API request failed: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in CoinGecko API request: {e}")
            return None
    
    def get_price(self, asset_symbol: str) -> Optional[float]:
        """
        Fetch the current price for an asset in USD.
        
        This method uses caching to reduce API calls. Cached prices are valid
        for 5 minutes.
        
        Args:
            asset_symbol: Asset symbol (e.g., 'BTC', 'ETH', 'SOL')
            
        Returns:
            Current price in USD or None on error
            
        Examples:
            >>> client = CoinGeckoClient()
            >>> price = client.get_price('BTC')
            >>> print(f"Bitcoin price: ${price}")
            Bitcoin price: $45000.50
        """
        asset_symbol = asset_symbol.upper()
        
        # Check cache first
        if asset_symbol in self.price_cache:
            cached_price, cached_time = self.price_cache[asset_symbol]
            if self._is_cache_valid(cached_time):
                return cached_price
        
        # Get CoinGecko ID
        coingecko_id = self._get_coingecko_id(asset_symbol)
        if not coingecko_id:
            print(f"Unknown asset symbol: {asset_symbol}")
            return None
        
        # Fetch from API
        params = {
            'ids': coingecko_id,
            'vs_currencies': 'usd'
        }
        
        data = self._make_request('simple/price', params)
        
        if not data or coingecko_id not in data:
            return None
        
        price = data[coingecko_id].get('usd')
        
        if price is not None:
            # Cache the result
            self.price_cache[asset_symbol] = (price, time.time())
        
        return price
    
    def get_24h_change(self, asset_symbol: str) -> Optional[float]:
        """
        Fetch the 24-hour price change percentage for an asset.
        
        This method uses caching to reduce API calls. Cached changes are valid
        for 5 minutes.
        
        Args:
            asset_symbol: Asset symbol (e.g., 'BTC', 'ETH', 'SOL')
            
        Returns:
            24-hour price change percentage or None on error
            
        Examples:
            >>> client = CoinGeckoClient()
            >>> change = client.get_24h_change('ETH')
            >>> print(f"Ethereum 24h change: {change}%")
            Ethereum 24h change: 5.5%
        """
        asset_symbol = asset_symbol.upper()
        
        # Check cache first
        if asset_symbol in self.change_cache:
            cached_change, cached_time = self.change_cache[asset_symbol]
            if self._is_cache_valid(cached_time):
                return cached_change
        
        # Get CoinGecko ID
        coingecko_id = self._get_coingecko_id(asset_symbol)
        if not coingecko_id:
            print(f"Unknown asset symbol: {asset_symbol}")
            return None
        
        # Fetch from API
        params = {
            'ids': coingecko_id,
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }
        
        data = self._make_request('simple/price', params)
        
        if not data or coingecko_id not in data:
            return None
        
        change = data[coingecko_id].get('usd_24h_change')
        
        if change is not None:
            # Cache the result
            self.change_cache[asset_symbol] = (change, time.time())
        
        return change
    
    def get_price_and_change(self, asset_symbol: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Fetch both current price and 24-hour change in a single API call.
        
        This is more efficient than calling get_price() and get_24h_change()
        separately when you need both values.
        
        Args:
            asset_symbol: Asset symbol (e.g., 'BTC', 'ETH', 'SOL')
            
        Returns:
            Tuple of (price, change_percentage) or (None, None) on error
            
        Examples:
            >>> client = CoinGeckoClient()
            >>> price, change = client.get_price_and_change('BTC')
            >>> print(f"BTC: ${price} ({change:+.2f}%)")
            BTC: $45000.50 (+5.50%)
        """
        asset_symbol = asset_symbol.upper()
        
        # Check if both values are cached and valid
        price_cached = asset_symbol in self.price_cache
        change_cached = asset_symbol in self.change_cache
        
        if price_cached and change_cached:
            cached_price, price_time = self.price_cache[asset_symbol]
            cached_change, change_time = self.change_cache[asset_symbol]
            
            if self._is_cache_valid(price_time) and self._is_cache_valid(change_time):
                return cached_price, cached_change
        
        # Get CoinGecko ID
        coingecko_id = self._get_coingecko_id(asset_symbol)
        if not coingecko_id:
            print(f"Unknown asset symbol: {asset_symbol}")
            return None, None
        
        # Fetch from API
        params = {
            'ids': coingecko_id,
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }
        
        data = self._make_request('simple/price', params)
        
        if not data or coingecko_id not in data:
            return None, None
        
        price = data[coingecko_id].get('usd')
        change = data[coingecko_id].get('usd_24h_change')
        
        # Cache both results
        current_time = time.time()
        if price is not None:
            self.price_cache[asset_symbol] = (price, current_time)
        if change is not None:
            self.change_cache[asset_symbol] = (change, current_time)
        
        return price, change
    
    def clear_cache(self):
        """
        Clear all cached price and change data.
        
        This can be useful for testing or when you need to force fresh data
        from the API.
        """
        self.price_cache.clear()
        self.change_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get statistics about the current cache state.
        
        Returns:
            Dictionary with cache statistics
            
        Examples:
            >>> client = CoinGeckoClient()
            >>> client.get_price('BTC')
            >>> stats = client.get_cache_stats()
            >>> print(stats)
            {'price_cache_size': 1, 'change_cache_size': 0}
        """
        return {
            'price_cache_size': len(self.price_cache),
            'change_cache_size': len(self.change_cache)
        }
