"""
Validation utilities for user input.

This module provides validation functions for wallet addresses, amounts, URLs,
and asset symbols to ensure data integrity and prevent errors.
"""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse


# Ethereum address regex: 0x followed by 40 hexadecimal characters
ETHEREUM_ADDRESS_PATTERN = re.compile(r'^0x[a-fA-F0-9]{40}$')

# Supported asset symbols
SUPPORTED_ASSETS = {
    'ETH', 'BTC', 'SOL', 'USDC', 'SPY', 'QQQ'
}

# Supported currencies for transactions
SUPPORTED_CURRENCIES = {'ETH', 'USDC'}


def validate_wallet_address(address: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an Ethereum wallet address format.
    
    Args:
        address: The wallet address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if address is valid, False otherwise
        - error_message: None if valid, error description if invalid
        
    Examples:
        >>> validate_wallet_address("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
        (False, "Invalid wallet address format. Address must be 42 characters long.")
        
        >>> validate_wallet_address("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0")
        (True, None)
    """
    if not address:
        return False, "Wallet address cannot be empty."
    
    if not isinstance(address, str):
        return False, "Wallet address must be a string."
    
    # Remove any whitespace
    address = address.strip()
    
    if not address.startswith('0x'):
        return False, "Invalid wallet address format. Address must start with '0x'."
    
    if len(address) != 42:
        return False, "Invalid wallet address format. Address must be 42 characters long."
    
    if not ETHEREUM_ADDRESS_PATTERN.match(address):
        return False, "Invalid wallet address format. Address must contain only hexadecimal characters."
    
    return True, None


def validate_amount(amount: any) -> Tuple[bool, Optional[str]]:
    """
    Validate a transaction amount.
    
    Args:
        amount: The amount to validate (can be string, int, or float)
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if amount is valid, False otherwise
        - error_message: None if valid, error description if invalid
        
    Examples:
        >>> validate_amount("10.5")
        (True, None)
        
        >>> validate_amount(-5)
        (False, "Amount must be positive.")
        
        >>> validate_amount("abc")
        (False, "Amount must be a valid number.")
    """
    if amount is None:
        return False, "Amount cannot be empty."
    
    # Try to convert to float
    try:
        amount_float = float(amount)
    except (ValueError, TypeError):
        return False, "Amount must be a valid number."
    
    # Check if positive
    if amount_float <= 0:
        return False, "Amount must be positive."
    
    # Check for reasonable upper bound (to prevent overflow)
    if amount_float > 1e15:
        return False, "Amount is too large."
    
    return True, None


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a URL format.
    
    Args:
        url: The URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if URL is valid, False otherwise
        - error_message: None if valid, error description if invalid
        
    Examples:
        >>> validate_url("https://example.com/article")
        (True, None)
        
        >>> validate_url("not a url")
        (False, "Invalid URL format. URL must include a scheme (http:// or https://).")
    """
    if not url:
        return False, "URL cannot be empty."
    
    if not isinstance(url, str):
        return False, "URL must be a string."
    
    # Remove any whitespace
    url = url.strip()
    
    try:
        parsed = urlparse(url)
        
        # Check if scheme is present and valid
        if not parsed.scheme:
            return False, "Invalid URL format. URL must include a scheme (http:// or https://)."
        
        if parsed.scheme not in ['http', 'https']:
            return False, "Invalid URL format. Only http:// and https:// schemes are supported."
        
        # Check if netloc (domain) is present
        if not parsed.netloc:
            return False, "Invalid URL format. URL must include a domain name."
        
        # Basic domain validation
        if '.' not in parsed.netloc:
            return False, "Invalid URL format. Domain must contain at least one dot."
        
        return True, None
        
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"


def validate_asset_symbol(symbol: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an asset symbol.
    
    Args:
        symbol: The asset symbol to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if symbol is valid, False otherwise
        - error_message: None if valid, error description if invalid
        
    Examples:
        >>> validate_asset_symbol("ETH")
        (True, None)
        
        >>> validate_asset_symbol("INVALID")
        (False, "Invalid asset symbol. Supported assets: BTC, ETH, QQQ, SOL, SPY, USDC")
    """
    if not symbol:
        return False, "Asset symbol cannot be empty."
    
    if not isinstance(symbol, str):
        return False, "Asset symbol must be a string."
    
    # Convert to uppercase for comparison
    symbol = symbol.strip().upper()
    
    if symbol not in SUPPORTED_ASSETS:
        supported_list = ', '.join(sorted(SUPPORTED_ASSETS))
        return False, f"Invalid asset symbol. Supported assets: {supported_list}"
    
    return True, None


def validate_currency(currency: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a transaction currency.
    
    Args:
        currency: The currency to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if currency is valid, False otherwise
        - error_message: None if valid, error description if invalid
        
    Examples:
        >>> validate_currency("ETH")
        (True, None)
        
        >>> validate_currency("BTC")
        (False, "Invalid currency. Supported currencies: ETH, USDC")
    """
    if not currency:
        return False, "Currency cannot be empty."
    
    if not isinstance(currency, str):
        return False, "Currency must be a string."
    
    # Convert to uppercase for comparison
    currency = currency.strip().upper()
    
    if currency not in SUPPORTED_CURRENCIES:
        supported_list = ', '.join(sorted(SUPPORTED_CURRENCIES))
        return False, f"Invalid currency. Supported currencies: {supported_list}"
    
    return True, None


def validate_recurrence(recurrence: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a payment recurrence value.
    
    Args:
        recurrence: The recurrence to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if recurrence is valid, False otherwise
        - error_message: None if valid, error description if invalid
        
    Examples:
        >>> validate_recurrence("weekly")
        (True, None)
        
        >>> validate_recurrence("yearly")
        (False, "Invalid recurrence. Supported values: daily, monthly, once, weekly")
    """
    valid_recurrences = {'once', 'daily', 'weekly', 'monthly'}
    
    if not recurrence:
        return False, "Recurrence cannot be empty."
    
    if not isinstance(recurrence, str):
        return False, "Recurrence must be a string."
    
    # Convert to lowercase for comparison
    recurrence = recurrence.strip().lower()
    
    if recurrence not in valid_recurrences:
        supported_list = ', '.join(sorted(valid_recurrences))
        return False, f"Invalid recurrence. Supported values: {supported_list}"
    
    return True, None


def validate_alert_direction(direction: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a price alert direction.
    
    Args:
        direction: The direction to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if direction is valid, False otherwise
        - error_message: None if valid, error description if invalid
        
    Examples:
        >>> validate_alert_direction("above")
        (True, None)
        
        >>> validate_alert_direction("up")
        (False, "Invalid direction. Supported values: above, below")
    """
    valid_directions = {'above', 'below'}
    
    if not direction:
        return False, "Direction cannot be empty."
    
    if not isinstance(direction, str):
        return False, "Direction must be a string."
    
    # Convert to lowercase for comparison
    direction = direction.strip().lower()
    
    if direction not in valid_directions:
        supported_list = ', '.join(sorted(valid_directions))
        return False, f"Invalid direction. Supported values: {supported_list}"
    
    return True, None
