"""
Unit tests for the Configuration module.
"""

import os
import sys
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from config import Configuration


class TestConfiguration:
    """Test suite for Configuration class"""
    
    def test_from_env_success(self, monkeypatch):
        """Test successful loading from environment variables"""
        # Set up environment variables
        monkeypatch.setenv('TELEGRAM_TOKEN', '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11')
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test-key')
        monkeypatch.setenv('WAAIAS_API_KEY', 'waaias-test-key')
        monkeypatch.setenv('X402_PRIVATE_KEY', '0x' + 'a' * 64)
        monkeypatch.setenv('DYNAMODB_TABLE', 'telegram-bot-users')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('COINGECKO_API_KEY', 'cg-test-key')
        
        # Load configuration
        config = Configuration.from_env()
        
        # Verify all fields are set
        assert config.telegram_token == '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'
        assert config.anthropic_api_key == 'sk-ant-test-key'
        assert config.waaias_api_key == 'waaias-test-key'
        assert config.x402_private_key == '0x' + 'a' * 64
        assert config.dynamodb_table == 'telegram-bot-users'
        assert config.aws_region == 'us-east-1'
        assert config.coingecko_api_key == 'cg-test-key'
    
    def test_from_env_missing_variable(self, monkeypatch):
        """Test that missing environment variable raises KeyError"""
        # Set only some variables
        monkeypatch.setenv('TELEGRAM_TOKEN', 'test-token')
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key')
        # Missing other required variables
        
        with pytest.raises(KeyError):
            Configuration.from_env()
    
    def test_validate_success(self):
        """Test validation passes for valid configuration"""
        config = Configuration(
            telegram_token='123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11',
            anthropic_api_key='sk-ant-test-key',
            waaias_api_key='waaias-test-key',
            x402_private_key='0x' + 'a' * 64,
            dynamodb_table='telegram-bot-users',
            aws_region='us-east-1',
            coingecko_api_key='cg-test-key'
        )
        
        errors = config.validate()
        assert errors == []
    
    def test_validate_empty_fields(self):
        """Test validation fails for empty fields"""
        config = Configuration(
            telegram_token='',
            anthropic_api_key='',
            waaias_api_key='',
            x402_private_key='',
            dynamodb_table='',
            aws_region='',
            coingecko_api_key=''
        )
        
        errors = config.validate()
        assert len(errors) == 7
        assert any('telegram_token' in err for err in errors)
        assert any('anthropic_api_key' in err for err in errors)
        assert any('waaias_api_key' in err for err in errors)
        assert any('x402_private_key' in err for err in errors)
        assert any('dynamodb_table' in err for err in errors)
        assert any('aws_region' in err for err in errors)
        assert any('coingecko_api_key' in err for err in errors)
    
    def test_validate_invalid_telegram_token(self):
        """Test validation fails for invalid Telegram token format"""
        config = Configuration(
            telegram_token='invalid-token-without-colon',
            anthropic_api_key='sk-ant-test-key',
            waaias_api_key='waaias-test-key',
            x402_private_key='0x' + 'a' * 64,
            dynamodb_table='telegram-bot-users',
            aws_region='us-east-1',
            coingecko_api_key='cg-test-key'
        )
        
        errors = config.validate()
        assert len(errors) == 1
        assert 'telegram_token' in errors[0]
        assert 'invalid' in errors[0]
    
    def test_validate_invalid_private_key_length(self):
        """Test validation fails for invalid private key length"""
        config = Configuration(
            telegram_token='123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11',
            anthropic_api_key='sk-ant-test-key',
            waaias_api_key='waaias-test-key',
            x402_private_key='0x123',  # Too short
            dynamodb_table='telegram-bot-users',
            aws_region='us-east-1',
            coingecko_api_key='cg-test-key'
        )
        
        errors = config.validate()
        assert len(errors) == 1
        assert 'x402_private_key' in errors[0]
        assert 'invalid length' in errors[0]
    
    def test_validate_private_key_without_prefix(self):
        """Test validation passes for private key without 0x prefix"""
        config = Configuration(
            telegram_token='123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11',
            anthropic_api_key='sk-ant-test-key',
            waaias_api_key='waaias-test-key',
            x402_private_key='a' * 64,  # Without 0x prefix
            dynamodb_table='telegram-bot-users',
            aws_region='us-east-1',
            coingecko_api_key='cg-test-key'
        )
        
        errors = config.validate()
        assert errors == []
    
    def test_configuration_dataclass_fields(self):
        """Test that Configuration has all required fields"""
        config = Configuration(
            telegram_token='test',
            anthropic_api_key='test',
            waaias_api_key='test',
            x402_private_key='test',
            dynamodb_table='test',
            aws_region='test',
            coingecko_api_key='test'
        )
        
        # Verify all fields exist
        assert hasattr(config, 'telegram_token')
        assert hasattr(config, 'anthropic_api_key')
        assert hasattr(config, 'waaias_api_key')
        assert hasattr(config, 'x402_private_key')
        assert hasattr(config, 'dynamodb_table')
        assert hasattr(config, 'aws_region')
        assert hasattr(config, 'coingecko_api_key')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
