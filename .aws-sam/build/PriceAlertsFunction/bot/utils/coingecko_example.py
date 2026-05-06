"""
Example usage of the CoinGecko API client.

This script demonstrates how to use the CoinGeckoClient to fetch
cryptocurrency prices and 24-hour changes.
"""

from coingecko_client import CoinGeckoClient
import os


def main():
    """Demonstrate CoinGecko client usage."""
    
    # Initialize client (optionally with API key from environment)
    api_key = os.environ.get('COINGECKO_API_KEY')
    client = CoinGeckoClient(api_key=api_key)
    
    print("=== CoinGecko API Client Example ===\n")
    
    # Example 1: Get current price
    print("1. Fetching Bitcoin price...")
    btc_price = client.get_price('BTC')
    if btc_price:
        print(f"   Bitcoin: ${btc_price:,.2f}\n")
    else:
        print("   Failed to fetch Bitcoin price\n")
    
    # Example 2: Get 24-hour change
    print("2. Fetching Ethereum 24h change...")
    eth_change = client.get_24h_change('ETH')
    if eth_change is not None:
        print(f"   Ethereum 24h change: {eth_change:+.2f}%\n")
    else:
        print("   Failed to fetch Ethereum change\n")
    
    # Example 3: Get both price and change efficiently
    print("3. Fetching Solana price and change...")
    sol_price, sol_change = client.get_price_and_change('SOL')
    if sol_price and sol_change is not None:
        print(f"   Solana: ${sol_price:,.2f} ({sol_change:+.2f}%)\n")
    else:
        print("   Failed to fetch Solana data\n")
    
    # Example 4: Demonstrate caching
    print("4. Demonstrating cache (second call should be instant)...")
    print("   First call (hits API)...")
    client.get_price('BTC')
    
    print("   Second call (uses cache)...")
    btc_price_cached = client.get_price('BTC')
    print(f"   Bitcoin (cached): ${btc_price_cached:,.2f}\n")
    
    # Example 5: Cache statistics
    print("5. Cache statistics:")
    stats = client.get_cache_stats()
    print(f"   Price cache entries: {stats['price_cache_size']}")
    print(f"   Change cache entries: {stats['change_cache_size']}\n")
    
    # Example 6: Multiple assets for market snapshot
    print("6. Market snapshot for portfolio assets:")
    assets = ['BTC', 'ETH', 'SOL', 'USDC']
    for asset in assets:
        price, change = client.get_price_and_change(asset)
        if price and change is not None:
            indicator = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
            print(f"   {asset}: ${price:,.2f} {indicator} {change:+.2f}%")
        else:
            print(f"   {asset}: Data unavailable")
    
    print("\n=== Example Complete ===")


if __name__ == '__main__':
    main()
