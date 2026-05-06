"""
Unit tests for formatting utilities.
"""

import pytest
from datetime import datetime, timezone
from bot.utils.formatting import (
    format_balance,
    format_usd_value,
    format_timestamp,
    format_relative_time,
    format_transaction,
    format_address,
    format_tx_hash,
    format_percentage,
    format_price_change,
    format_portfolio_item,
    format_scheduled_payment,
    format_price_alert,
    format_contact,
    format_error_message
)


class TestFormatBalance:
    """Tests for balance formatting."""
    
    def test_basic_formatting(self):
        """Test basic balance formatting."""
        assert format_balance(1.2346, "ETH") == "1.2346 ETH"
        assert format_balance(0.5, "USDC") == "0.5 USDC"
    
    def test_zero_balance(self):
        """Test zero balance formatting."""
        assert format_balance(0, "ETH") == "0 ETH"
    
    def test_large_balance(self):
        """Test large balance with thousand separators."""
        result = format_balance(1234.5678, "USDC", decimals=2)
        assert "1,234" in result
        assert "USDC" in result
    
    def test_trailing_zeros_removed(self):
        """Test that trailing zeros are removed."""
        assert format_balance(1.5000, "ETH") == "1.5 ETH"
        assert format_balance(1.0, "ETH") == "1 ETH"
    
    def test_custom_decimals(self):
        """Test custom decimal places."""
        assert format_balance(1.23456789, "ETH", decimals=2) == "1.23 ETH"
        assert format_balance(1.23456789, "ETH", decimals=6) == "1.234568 ETH"


class TestFormatUsdValue:
    """Tests for USD value formatting."""
    
    def test_basic_formatting(self):
        """Test basic USD formatting."""
        assert format_usd_value(1234.56) == "$1,234.56"
        assert format_usd_value(0.5) == "$0.50"
    
    def test_zero_value(self):
        """Test zero value formatting."""
        assert format_usd_value(0) == "$0.00"
    
    def test_large_value(self):
        """Test large value with thousand separators."""
        assert format_usd_value(1000000) == "$1,000,000.00"
    
    def test_custom_decimals(self):
        """Test custom decimal places."""
        assert format_usd_value(1234.5678, decimals=4) == "$1,234.5678"


class TestFormatTimestamp:
    """Tests for timestamp formatting."""
    
    def test_datetime_format(self):
        """Test full datetime formatting."""
        # 2024-01-01 00:00:00 UTC
        timestamp = 1704067200
        result = format_timestamp(timestamp, "datetime")
        assert "2024-01-01" in result
        assert "00:00:00" in result
        assert "UTC" in result
    
    def test_date_format(self):
        """Test date-only formatting."""
        timestamp = 1704067200
        result = format_timestamp(timestamp, "date")
        assert result == "2024-01-01"
    
    def test_time_format(self):
        """Test time-only formatting."""
        timestamp = 1704067200
        result = format_timestamp(timestamp, "time")
        assert "00:00:00" in result
        assert "UTC" in result
    
    def test_invalid_timestamp(self):
        """Test invalid timestamp handling."""
        result = format_timestamp(-1, "datetime")
        assert "Invalid" in result or "1969" in result  # Depends on system


class TestFormatAddress:
    """Tests for address formatting."""
    
    def test_basic_formatting(self):
        """Test basic address shortening."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        result = format_address(address)
        assert result == "0x742d...bEb0"
    
    def test_short_address(self):
        """Test that short addresses are not shortened."""
        address = "0x1234"
        result = format_address(address)
        assert result == address
    
    def test_custom_lengths(self):
        """Test custom prefix and suffix lengths."""
        address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        result = format_address(address, prefix_len=8, suffix_len=6)
        assert result == "0x742d35...f0bEb0"


class TestFormatTxHash:
    """Tests for transaction hash formatting."""
    
    def test_basic_formatting(self):
        """Test basic tx hash shortening."""
        tx_hash = "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        result = format_tx_hash(tx_hash)
        assert "0xabcdef" in result
        assert "..." in result
        assert "567890" in result
    
    def test_short_hash(self):
        """Test that short hashes are not shortened."""
        tx_hash = "0x1234"
        result = format_tx_hash(tx_hash)
        assert result == tx_hash


class TestFormatPercentage:
    """Tests for percentage formatting."""
    
    def test_positive_percentage(self):
        """Test positive percentage formatting."""
        assert format_percentage(5.5) == "+5.50%"
    
    def test_negative_percentage(self):
        """Test negative percentage formatting."""
        assert format_percentage(-2.3) == "-2.30%"
    
    def test_zero_percentage(self):
        """Test zero percentage formatting."""
        assert format_percentage(0) == "0.00%"
    
    def test_without_sign(self):
        """Test percentage formatting without sign."""
        assert format_percentage(5.5, include_sign=False) == "5.50%"
    
    def test_custom_decimals(self):
        """Test custom decimal places."""
        assert format_percentage(5.555, decimals=1) == "+5.6%"


class TestFormatPriceChange:
    """Tests for price change formatting."""
    
    def test_positive_change(self):
        """Test positive price change with green indicator."""
        result = format_price_change(5.5)
        assert "🟢" in result
        assert "+5.50%" in result
    
    def test_negative_change(self):
        """Test negative price change with red indicator."""
        result = format_price_change(-2.3)
        assert "🔴" in result
        assert "-2.30%" in result
    
    def test_zero_change(self):
        """Test zero price change with neutral indicator."""
        result = format_price_change(0)
        assert "⚪" in result
        assert "0.00%" in result


class TestFormatTransaction:
    """Tests for transaction formatting."""
    
    def test_send_transaction(self):
        """Test send transaction formatting."""
        tx = {
            "type": "send",
            "amount": 1.5,
            "currency": "ETH",
            "counterparty": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            "timestamp": 1704067200
        }
        result = format_transaction(tx)
        assert "📤" in result
        assert "Sent" in result
        assert "1.5 ETH" in result
        assert "To:" in result
        assert "0x742d...bEb0" in result
    
    def test_receive_transaction(self):
        """Test receive transaction formatting."""
        tx = {
            "type": "receive",
            "amount": 2.0,
            "currency": "USDC",
            "counterparty": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            "timestamp": 1704067200
        }
        result = format_transaction(tx)
        assert "📥" in result
        assert "Received" in result
        assert "2 USDC" in result
        assert "From:" in result
    
    def test_transaction_with_hash(self):
        """Test transaction with tx hash."""
        tx = {
            "type": "send",
            "amount": 1.5,
            "currency": "ETH",
            "counterparty": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            "timestamp": 1704067200,
            "tx_hash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        }
        result = format_transaction(tx)
        assert "TX:" in result
        assert "0xabcdef" in result


class TestFormatPortfolioItem:
    """Tests for portfolio item formatting."""
    
    def test_profitable_position(self):
        """Test formatting of profitable position."""
        result = format_portfolio_item("ETH", 1.5, 3000, 3600)
        assert "ETH" in result
        assert "1.5" in result
        assert "$3,600" in result
        assert "🟢" in result
        assert "+20.00%" in result
    
    def test_losing_position(self):
        """Test formatting of losing position."""
        result = format_portfolio_item("BTC", 0.1, 5000, 4000)
        assert "BTC" in result
        assert "0.1" in result
        assert "$4,000" in result
        assert "🔴" in result
        assert "-20.00%" in result


class TestFormatScheduledPayment:
    """Tests for scheduled payment formatting."""
    
    def test_basic_formatting(self):
        """Test basic scheduled payment formatting."""
        payment = {
            "contact_name": "Marcus",
            "amount": 10,
            "currency": "USDC",
            "recurrence": "weekly",
            "next_run": 1704067200
        }
        result = format_scheduled_payment(payment)
        assert "💰" in result
        assert "10 USDC" in result
        assert "Marcus" in result
        assert "Weekly" in result
        assert "Next:" in result


class TestFormatPriceAlert:
    """Tests for price alert formatting."""
    
    def test_above_alert(self):
        """Test above price alert formatting."""
        alert = {
            "asset_symbol": "BTC",
            "target_price": 100000,
            "direction": "above"
        }
        result = format_price_alert(alert)
        assert "🔔" in result
        assert "BTC" in result
        assert "above" in result
        assert "$100,000" in result
        assert "⬆️" in result
    
    def test_below_alert(self):
        """Test below price alert formatting."""
        alert = {
            "asset_symbol": "ETH",
            "target_price": 2000,
            "direction": "below"
        }
        result = format_price_alert(alert)
        assert "🔔" in result
        assert "ETH" in result
        assert "below" in result
        assert "$2,000" in result
        assert "⬇️" in result


class TestFormatContact:
    """Tests for contact formatting."""
    
    def test_basic_formatting(self):
        """Test basic contact formatting."""
        contact = {
            "name": "Marcus",
            "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        }
        result = format_contact(contact)
        assert "👤" in result
        assert "Marcus" in result
        assert "📍" in result
        assert "0x742d...bEb0" in result


class TestFormatErrorMessage:
    """Tests for error message formatting."""
    
    def test_validation_error(self):
        """Test validation error formatting."""
        result = format_error_message("validation", "Invalid wallet address")
        assert "❌" in result
        assert "Validation Error" in result
        assert "Invalid wallet address" in result
    
    def test_network_error(self):
        """Test network error formatting."""
        result = format_error_message("network")
        assert "❌" in result
        assert "Network Error" in result
        assert "try again" in result
    
    def test_insufficient_balance_error(self):
        """Test insufficient balance error formatting."""
        result = format_error_message("insufficient_balance")
        assert "❌" in result
        assert "Insufficient Balance" in result
    
    def test_unknown_error(self):
        """Test unknown error formatting."""
        result = format_error_message("unknown_type")
        assert "❌" in result
        assert "Error Occurred" in result
    
    def test_error_with_details(self):
        """Test error with additional details."""
        result = format_error_message("api_timeout", "CoinGecko API timeout")
        assert "❌" in result
        assert "Service Temporarily Unavailable" in result
        assert "CoinGecko API timeout" in result
