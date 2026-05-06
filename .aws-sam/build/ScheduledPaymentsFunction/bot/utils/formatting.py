"""
Formatting utilities for displaying data to users.

This module provides formatting functions for balances, timestamps, transaction
details, and other data to ensure consistent and user-friendly presentation.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


def format_balance(amount: float, currency: str, decimals: int = 4) -> str:
    """
    Format a balance amount with currency symbol.
    
    Args:
        amount: The balance amount
        currency: The currency symbol (e.g., 'ETH', 'USDC')
        decimals: Number of decimal places to display (default: 4)
        
    Returns:
        Formatted balance string
        
    Examples:
        >>> format_balance(1.23456789, "ETH")
        "1.2346 ETH"
        
        >>> format_balance(1000.5, "USDC", decimals=2)
        "1,000.50 USDC"
    """
    if amount == 0:
        return f"0 {currency}"
    
    # Format with specified decimals
    if amount >= 1000:
        # Add thousand separators for large amounts
        formatted = f"{amount:,.{decimals}f}"
    else:
        formatted = f"{amount:.{decimals}f}"
    
    # Remove trailing zeros after decimal point
    if '.' in formatted:
        formatted = formatted.rstrip('0').rstrip('.')
    
    return f"{formatted} {currency}"


def format_usd_value(amount: float, decimals: int = 2) -> str:
    """
    Format a USD value with dollar sign and thousand separators.
    
    Args:
        amount: The USD amount
        decimals: Number of decimal places to display (default: 2)
        
    Returns:
        Formatted USD string
        
    Examples:
        >>> format_usd_value(1234.56)
        "$1,234.56"
        
        >>> format_usd_value(0.5)
        "$0.50"
    """
    if amount == 0:
        return "$0.00"
    
    # Format with thousand separators
    formatted = f"${amount:,.{decimals}f}"
    
    return formatted


def format_timestamp(timestamp: int, format_type: str = "datetime") -> str:
    """
    Format a Unix timestamp into a human-readable string.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        format_type: Type of format to use:
            - "datetime": Full date and time (default)
            - "date": Date only
            - "time": Time only
            - "relative": Relative time (e.g., "2 hours ago")
            
    Returns:
        Formatted timestamp string
        
    Examples:
        >>> format_timestamp(1704067200, "datetime")
        "2024-01-01 00:00:00 UTC"
        
        >>> format_timestamp(1704067200, "date")
        "2024-01-01"
    """
    try:
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        
        if format_type == "datetime":
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        elif format_type == "date":
            return dt.strftime("%Y-%m-%d")
        elif format_type == "time":
            return dt.strftime("%H:%M:%S UTC")
        elif format_type == "relative":
            return format_relative_time(timestamp)
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            
    except (ValueError, OSError) as e:
        return f"Invalid timestamp: {timestamp}"


def format_relative_time(timestamp: int) -> str:
    """
    Format a Unix timestamp as relative time (e.g., "2 hours ago").
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        
    Returns:
        Relative time string
        
    Examples:
        >>> # Assuming current time is 1704070800
        >>> format_relative_time(1704067200)
        "1 hour ago"
    """
    try:
        now = datetime.now(timezone.utc)
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        diff = now - dt
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        else:
            months = int(seconds / 2592000)
            return f"{months} month{'s' if months != 1 else ''} ago"
            
    except (ValueError, OSError):
        return "unknown time"


def format_transaction(transaction: Dict[str, Any]) -> str:
    """
    Format a transaction record for display.
    
    Args:
        transaction: Dictionary containing transaction details with keys:
            - type: "send" or "receive"
            - amount: Transaction amount
            - currency: Currency symbol
            - counterparty: Other party's address
            - timestamp: Unix timestamp
            - tx_hash: Transaction hash (optional)
            
    Returns:
        Formatted transaction string
        
    Examples:
        >>> tx = {
        ...     "type": "send",
        ...     "amount": 1.5,
        ...     "currency": "ETH",
        ...     "counterparty": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        ...     "timestamp": 1704067200
        ... }
        >>> format_transaction(tx)
        "📤 Sent 1.5 ETH\\nTo: 0x742d...bEb0\\n🕐 2024-01-01 00:00:00 UTC"
    """
    tx_type = transaction.get("type", "unknown")
    amount = transaction.get("amount", 0)
    currency = transaction.get("currency", "")
    counterparty = transaction.get("counterparty", "")
    timestamp = transaction.get("timestamp", 0)
    tx_hash = transaction.get("tx_hash")
    
    # Choose emoji based on transaction type
    if tx_type == "send":
        emoji = "📤"
        action = "Sent"
        party_label = "To"
    elif tx_type == "receive":
        emoji = "📥"
        action = "Received"
        party_label = "From"
    else:
        emoji = "💱"
        action = "Transaction"
        party_label = "Party"
    
    # Format the transaction
    lines = [
        f"{emoji} {action} {format_balance(amount, currency)}",
        f"{party_label}: {format_address(counterparty)}",
        f"🕐 {format_timestamp(timestamp, 'datetime')}"
    ]
    
    if tx_hash:
        lines.append(f"TX: {format_tx_hash(tx_hash)}")
    
    return "\n".join(lines)


def format_address(address: str, prefix_len: int = 6, suffix_len: int = 4) -> str:
    """
    Format a wallet address with ellipsis for readability.
    
    Args:
        address: Full wallet address
        prefix_len: Number of characters to show at start (default: 6)
        suffix_len: Number of characters to show at end (default: 4)
        
    Returns:
        Shortened address string
        
    Examples:
        >>> format_address("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0")
        "0x742d...bEb0"
    """
    if not address or len(address) <= prefix_len + suffix_len:
        return address
    
    return f"{address[:prefix_len]}...{address[-suffix_len:]}"


def format_tx_hash(tx_hash: str, prefix_len: int = 8, suffix_len: int = 6) -> str:
    """
    Format a transaction hash with ellipsis for readability.
    
    Args:
        tx_hash: Full transaction hash
        prefix_len: Number of characters to show at start (default: 8)
        suffix_len: Number of characters to show at end (default: 6)
        
    Returns:
        Shortened transaction hash string
        
    Examples:
        >>> format_tx_hash("0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890")
        "0xabcdef...567890"
    """
    if not tx_hash or len(tx_hash) <= prefix_len + suffix_len:
        return tx_hash
    
    return f"{tx_hash[:prefix_len]}...{tx_hash[-suffix_len:]}"


def format_percentage(value: float, decimals: int = 2, include_sign: bool = True) -> str:
    """
    Format a percentage value with optional sign and color indicator.
    
    Args:
        value: The percentage value (e.g., 5.5 for 5.5%)
        decimals: Number of decimal places to display (default: 2)
        include_sign: Whether to include + sign for positive values (default: True)
        
    Returns:
        Formatted percentage string
        
    Examples:
        >>> format_percentage(5.5)
        "+5.50%"
        
        >>> format_percentage(-2.3)
        "-2.30%"
    """
    if value == 0:
        return "0.00%"
    
    sign = ""
    if include_sign and value > 0:
        sign = "+"
    
    formatted = f"{sign}{value:.{decimals}f}%"
    
    return formatted


def format_price_change(value: float, decimals: int = 2) -> str:
    """
    Format a price change with emoji indicator.
    
    Args:
        value: The percentage change value
        decimals: Number of decimal places to display (default: 2)
        
    Returns:
        Formatted price change string with emoji
        
    Examples:
        >>> format_price_change(5.5)
        "🟢 +5.50%"
        
        >>> format_price_change(-2.3)
        "🔴 -2.30%"
    """
    if value > 0:
        emoji = "🟢"
    elif value < 0:
        emoji = "🔴"
    else:
        emoji = "⚪"
    
    percentage = format_percentage(value, decimals=decimals, include_sign=True)
    
    return f"{emoji} {percentage}"


def format_portfolio_item(asset: str, quantity: float, cost_basis: float, 
                         current_value: float) -> str:
    """
    Format a portfolio item with profit/loss calculation.
    
    Args:
        asset: Asset symbol
        quantity: Amount held
        cost_basis: Original purchase value in USD
        current_value: Current value in USD
        
    Returns:
        Formatted portfolio item string
        
    Examples:
        >>> format_portfolio_item("ETH", 1.5, 3000, 3600)
        "ETH: 1.5\\nValue: $3,600.00\\nP/L: 🟢 +$600.00 (+20.00%)"
    """
    profit_loss = current_value - cost_basis
    profit_loss_pct = (profit_loss / cost_basis * 100) if cost_basis > 0 else 0
    
    lines = [
        f"{asset}: {format_balance(quantity, asset)}",
        f"Value: {format_usd_value(current_value)}",
        f"P/L: {format_price_change(profit_loss_pct)} {format_usd_value(abs(profit_loss))}"
    ]
    
    return "\n".join(lines)


def format_scheduled_payment(payment: Dict[str, Any]) -> str:
    """
    Format a scheduled payment for display.
    
    Args:
        payment: Dictionary containing payment details with keys:
            - contact_name: Name of recipient
            - amount: Payment amount
            - currency: Currency symbol
            - recurrence: Payment frequency
            - next_run: Unix timestamp of next execution
            
    Returns:
        Formatted scheduled payment string
        
    Examples:
        >>> payment = {
        ...     "contact_name": "Marcus",
        ...     "amount": 10,
        ...     "currency": "USDC",
        ...     "recurrence": "weekly",
        ...     "next_run": 1704067200
        ... }
        >>> format_scheduled_payment(payment)
        "💰 10 USDC to Marcus\\n📅 Weekly\\n⏰ Next: 2024-01-01 00:00:00 UTC"
    """
    contact_name = payment.get("contact_name", "Unknown")
    amount = payment.get("amount", 0)
    currency = payment.get("currency", "")
    recurrence = payment.get("recurrence", "once")
    next_run = payment.get("next_run", 0)
    
    lines = [
        f"💰 {format_balance(amount, currency)} to {contact_name}",
        f"📅 {recurrence.capitalize()}",
        f"⏰ Next: {format_timestamp(next_run, 'datetime')}"
    ]
    
    return "\n".join(lines)


def format_price_alert(alert: Dict[str, Any]) -> str:
    """
    Format a price alert for display.
    
    Args:
        alert: Dictionary containing alert details with keys:
            - asset_symbol: Asset symbol
            - target_price: Target price in USD
            - direction: "above" or "below"
            
    Returns:
        Formatted price alert string
        
    Examples:
        >>> alert = {
        ...     "asset_symbol": "BTC",
        ...     "target_price": 100000,
        ...     "direction": "above"
        ... }
        >>> format_price_alert(alert)
        "🔔 BTC above $100,000.00"
    """
    asset = alert.get("asset_symbol", "")
    target_price = alert.get("target_price", 0)
    direction = alert.get("direction", "above")
    
    direction_emoji = "⬆️" if direction == "above" else "⬇️"
    
    return f"🔔 {asset} {direction} {format_usd_value(target_price)} {direction_emoji}"


def format_contact(contact: Dict[str, Any]) -> str:
    """
    Format a contact for display.
    
    Args:
        contact: Dictionary containing contact details with keys:
            - name: Contact name
            - address: Wallet address
            
    Returns:
        Formatted contact string
        
    Examples:
        >>> contact = {
        ...     "name": "Marcus",
        ...     "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        ... }
        >>> format_contact(contact)
        "👤 Marcus\\n📍 0x742d...bEb0"
    """
    name = contact.get("name", "Unknown")
    address = contact.get("address", "")
    
    lines = [
        f"👤 {name}",
        f"📍 {format_address(address)}"
    ]
    
    return "\n".join(lines)


def format_error_message(error_type: str, details: Optional[str] = None) -> str:
    """
    Format an error message for display to users.
    
    Args:
        error_type: Type of error (e.g., "validation", "network", "insufficient_balance")
        details: Additional error details
        
    Returns:
        Formatted error message string
        
    Examples:
        >>> format_error_message("validation", "Invalid wallet address")
        "❌ Validation Error\\nInvalid wallet address"
        
        >>> format_error_message("network")
        "❌ Network Error\\nPlease try again later."
    """
    error_messages = {
        "validation": "❌ Validation Error",
        "network": "❌ Network Error\nPlease try again later.",
        "insufficient_balance": "❌ Insufficient Balance\nYou don't have enough funds for this transaction.",
        "api_timeout": "❌ Service Temporarily Unavailable\nPlease try again in a few moments.",
        "unknown": "❌ An Error Occurred\nPlease try again or contact support."
    }
    
    base_message = error_messages.get(error_type, error_messages["unknown"])
    
    if details:
        return f"{base_message}\n{details}"
    
    return base_message
