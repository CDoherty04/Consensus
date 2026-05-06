"""
Unit tests for validation utilities.
"""

import pytest
from bot.utils.validation import (
    validate_wallet_address,
    validate_amount,
    validate_url,
    validate_asset_symbol,
    validate_currency,
    validate_recurrence,
    validate_alert_direction
)


class TestValidateWalletAddress:
    """Tests for wallet address validation."""
    
    def test_valid_address(self):
        """Test validation of valid Ethereum addresses."""
        valid_addresses = [
            "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            "0x0000000000000000000000000000000000000000",
            "0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
            "0x1234567890abcdef1234567890abcdef12345678"
        ]
        
        for address in valid_addresses:
            is_valid, error = validate_wallet_address(address)
            assert is_valid is True, f"Address {address} should be valid"
            assert error is None
    
    def test_invalid_prefix(self):
        """Test addresses without 0x prefix."""
        is_valid, error = validate_wallet_address("742d35Cc6634C0532925a3b844Bc9e7595f0bEb0")
        assert is_valid is False
        assert "must start with '0x'" in error
    
    def test_invalid_length(self):
        """Test addresses with incorrect length."""
        # Too short
        is_valid, error = validate_wallet_address("0x742d35Cc")
        assert is_valid is False
        assert "42 characters" in error
        
        # Too long
        is_valid, error = validate_wallet_address("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb00")
        assert is_valid is False
        assert "42 characters" in error
    
    def test_invalid_characters(self):
        """Test addresses with non-hexadecimal characters."""
        is_valid, error = validate_wallet_address("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbG")
        assert is_valid is False
        assert "hexadecimal" in error
    
    def test_empty_address(self):
        """Test empty address."""
        is_valid, error = validate_wallet_address("")
        assert is_valid is False
        assert "cannot be empty" in error
    
    def test_whitespace_handling(self):
        """Test that whitespace is properly handled."""
        is_valid, error = validate_wallet_address("  0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0  ")
        assert is_valid is True
        assert error is None


class TestValidateAmount:
    """Tests for amount validation."""
    
    def test_valid_amounts(self):
        """Test validation of valid amounts."""
        valid_amounts = [
            1,
            1.5,
            0.001,
            "10",
            "10.5",
            100000
        ]
        
        for amount in valid_amounts:
            is_valid, error = validate_amount(amount)
            assert is_valid is True, f"Amount {amount} should be valid"
            assert error is None
    
    def test_negative_amount(self):
        """Test negative amounts."""
        is_valid, error = validate_amount(-5)
        assert is_valid is False
        assert "must be positive" in error
    
    def test_zero_amount(self):
        """Test zero amount."""
        is_valid, error = validate_amount(0)
        assert is_valid is False
        assert "must be positive" in error
    
    def test_non_numeric_amount(self):
        """Test non-numeric amounts."""
        is_valid, error = validate_amount("abc")
        assert is_valid is False
        assert "valid number" in error
    
    def test_none_amount(self):
        """Test None amount."""
        is_valid, error = validate_amount(None)
        assert is_valid is False
        assert "cannot be empty" in error
    
    def test_very_large_amount(self):
        """Test extremely large amounts."""
        is_valid, error = validate_amount(1e16)
        assert is_valid is False
        assert "too large" in error


class TestValidateUrl:
    """Tests for URL validation."""
    
    def test_valid_urls(self):
        """Test validation of valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://example.com/article",
            "https://sub.domain.example.com/path/to/article?param=value",
            "https://example.com:8080/path"
        ]
        
        for url in valid_urls:
            is_valid, error = validate_url(url)
            assert is_valid is True, f"URL {url} should be valid"
            assert error is None
    
    def test_missing_scheme(self):
        """Test URLs without scheme."""
        is_valid, error = validate_url("example.com")
        assert is_valid is False
        assert "scheme" in error
    
    def test_invalid_scheme(self):
        """Test URLs with invalid scheme."""
        is_valid, error = validate_url("ftp://example.com")
        assert is_valid is False
        assert "http" in error or "https" in error
    
    def test_missing_domain(self):
        """Test URLs without domain."""
        is_valid, error = validate_url("https://")
        assert is_valid is False
        assert "domain" in error
    
    def test_invalid_domain(self):
        """Test URLs with invalid domain."""
        is_valid, error = validate_url("https://invalid")
        assert is_valid is False
        assert "dot" in error
    
    def test_empty_url(self):
        """Test empty URL."""
        is_valid, error = validate_url("")
        assert is_valid is False
        assert "cannot be empty" in error
    
    def test_whitespace_handling(self):
        """Test that whitespace is properly handled."""
        is_valid, error = validate_url("  https://example.com  ")
        assert is_valid is True
        assert error is None


class TestValidateAssetSymbol:
    """Tests for asset symbol validation."""
    
    def test_valid_symbols(self):
        """Test validation of valid asset symbols."""
        valid_symbols = ['ETH', 'BTC', 'SOL', 'USDC', 'SPY', 'QQQ']
        
        for symbol in valid_symbols:
            is_valid, error = validate_asset_symbol(symbol)
            assert is_valid is True, f"Symbol {symbol} should be valid"
            assert error is None
    
    def test_case_insensitive(self):
        """Test that validation is case-insensitive."""
        is_valid, error = validate_asset_symbol("eth")
        assert is_valid is True
        assert error is None
    
    def test_invalid_symbol(self):
        """Test invalid asset symbols."""
        is_valid, error = validate_asset_symbol("INVALID")
        assert is_valid is False
        assert "Supported assets" in error
    
    def test_empty_symbol(self):
        """Test empty symbol."""
        is_valid, error = validate_asset_symbol("")
        assert is_valid is False
        assert "cannot be empty" in error


class TestValidateCurrency:
    """Tests for currency validation."""
    
    def test_valid_currencies(self):
        """Test validation of valid currencies."""
        valid_currencies = ['ETH', 'USDC']
        
        for currency in valid_currencies:
            is_valid, error = validate_currency(currency)
            assert is_valid is True, f"Currency {currency} should be valid"
            assert error is None
    
    def test_case_insensitive(self):
        """Test that validation is case-insensitive."""
        is_valid, error = validate_currency("eth")
        assert is_valid is True
        assert error is None
    
    def test_invalid_currency(self):
        """Test invalid currencies."""
        is_valid, error = validate_currency("BTC")
        assert is_valid is False
        assert "Supported currencies" in error
    
    def test_empty_currency(self):
        """Test empty currency."""
        is_valid, error = validate_currency("")
        assert is_valid is False
        assert "cannot be empty" in error


class TestValidateRecurrence:
    """Tests for recurrence validation."""
    
    def test_valid_recurrences(self):
        """Test validation of valid recurrence values."""
        valid_recurrences = ['once', 'daily', 'weekly', 'monthly']
        
        for recurrence in valid_recurrences:
            is_valid, error = validate_recurrence(recurrence)
            assert is_valid is True, f"Recurrence {recurrence} should be valid"
            assert error is None
    
    def test_case_insensitive(self):
        """Test that validation is case-insensitive."""
        is_valid, error = validate_recurrence("WEEKLY")
        assert is_valid is True
        assert error is None
    
    def test_invalid_recurrence(self):
        """Test invalid recurrence values."""
        is_valid, error = validate_recurrence("yearly")
        assert is_valid is False
        assert "Supported values" in error
    
    def test_empty_recurrence(self):
        """Test empty recurrence."""
        is_valid, error = validate_recurrence("")
        assert is_valid is False
        assert "cannot be empty" in error


class TestValidateAlertDirection:
    """Tests for alert direction validation."""
    
    def test_valid_directions(self):
        """Test validation of valid directions."""
        valid_directions = ['above', 'below']
        
        for direction in valid_directions:
            is_valid, error = validate_alert_direction(direction)
            assert is_valid is True, f"Direction {direction} should be valid"
            assert error is None
    
    def test_case_insensitive(self):
        """Test that validation is case-insensitive."""
        is_valid, error = validate_alert_direction("ABOVE")
        assert is_valid is True
        assert error is None
    
    def test_invalid_direction(self):
        """Test invalid directions."""
        is_valid, error = validate_alert_direction("up")
        assert is_valid is False
        assert "Supported values" in error
    
    def test_empty_direction(self):
        """Test empty direction."""
        is_valid, error = validate_alert_direction("")
        assert is_valid is False
        assert "cannot be empty" in error
