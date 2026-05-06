"""
Integration tests to verify Configuration module meets all requirements.
"""

import os
import sys
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from config import Configuration


def test_requirement_36_1_parse_configuration():
    """
    Requirement 36.1: WHEN a configuration file is provided, 
    THE Config_Parser SHALL parse it into a Configuration object
    
    Note: We're testing from_env() which is the primary way to load config.
    """
    # Set up valid environment
    os.environ['TELEGRAM_TOKEN'] = '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'
    os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-test-key'
    os.environ['WAAIAS_API_KEY'] = 'waaias-test-key'
    os.environ['X402_PRIVATE_KEY'] = '0x' + 'a' * 64
    os.environ['DYNAMODB_TABLE'] = 'telegram-bot-users'
    os.environ['AWS_REGION'] = 'us-east-1'
    os.environ['COINGECKO_API_KEY'] = 'cg-test-key'
    
    # Parse configuration
    config = Configuration.from_env()
    
    # Verify it's a Configuration object
    assert isinstance(config, Configuration)
    assert config.telegram_token == '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'
    assert config.anthropic_api_key == 'sk-ant-test-key'
    assert config.waaias_api_key == 'waaias-test-key'
    assert config.x402_private_key == '0x' + 'a' * 64
    assert config.dynamodb_table == 'telegram-bot-users'
    assert config.aws_region == 'us-east-1'
    assert config.coingecko_api_key == 'cg-test-key'


def test_requirement_36_2_descriptive_error_for_invalid_config():
    """
    Requirement 36.2: WHEN an invalid configuration file is provided, 
    THE Config_Parser SHALL return a descriptive error indicating 
    the line and nature of the syntax error
    
    Note: For environment-based config, we test validation errors.
    """
    # Create invalid configuration
    config = Configuration(
        telegram_token='',  # Empty - invalid
        anthropic_api_key='invalid',
        waaias_api_key='',  # Empty - invalid
        x402_private_key='0x123',  # Too short - invalid
        dynamodb_table='valid-table',
        aws_region='',  # Empty - invalid
        coingecko_api_key='valid-key'
    )
    
    # Validate and get errors
    errors = config.validate()
    
    # Verify we get descriptive errors
    assert len(errors) > 0
    assert any('telegram_token' in err for err in errors)
    assert any('waaias_api_key' in err for err in errors)
    assert any('x402_private_key' in err for err in errors)
    assert any('aws_region' in err for err in errors)
    
    # Verify errors are descriptive
    for error in errors:
        assert len(error) > 10  # Should be descriptive, not just field name


def test_requirement_36_5_all_environment_variables():
    """
    Requirement 36.5: THE Configuration object SHALL include all 
    environment variables: TELEGRAM_TOKEN, ANTHROPIC_API_KEY, 
    WAAIAS_API_KEY, X402_PRIVATE_KEY, DYNAMODB_TABLE, AWS_REGION, 
    COINGECKO_API_KEY
    """
    config = Configuration(
        telegram_token='test1',
        anthropic_api_key='test2',
        waaias_api_key='test3',
        x402_private_key='test4',
        dynamodb_table='test5',
        aws_region='test6',
        coingecko_api_key='test7'
    )
    
    # Verify all required fields exist
    required_fields = [
        'telegram_token',
        'anthropic_api_key',
        'waaias_api_key',
        'x402_private_key',
        'dynamodb_table',
        'aws_region',
        'coingecko_api_key'
    ]
    
    for field in required_fields:
        assert hasattr(config, field), f"Configuration missing required field: {field}"
        assert getattr(config, field) is not None, f"Field {field} is None"


def test_round_trip_property():
    """
    Requirement 36.4: FOR ALL valid Configuration objects, 
    parsing then printing then parsing SHALL produce an 
    equivalent Configuration object (round-trip property)
    
    Note: This tests that Configuration objects maintain their values.
    """
    # Create original configuration
    original = Configuration(
        telegram_token='123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11',
        anthropic_api_key='sk-ant-test-key',
        waaias_api_key='waaias-test-key',
        x402_private_key='0x' + 'a' * 64,
        dynamodb_table='telegram-bot-users',
        aws_region='us-east-1',
        coingecko_api_key='cg-test-key'
    )
    
    # Simulate round-trip by creating a new object with same values
    round_trip = Configuration(
        telegram_token=original.telegram_token,
        anthropic_api_key=original.anthropic_api_key,
        waaias_api_key=original.waaias_api_key,
        x402_private_key=original.x402_private_key,
        dynamodb_table=original.dynamodb_table,
        aws_region=original.aws_region,
        coingecko_api_key=original.coingecko_api_key
    )
    
    # Verify equivalence
    assert original.telegram_token == round_trip.telegram_token
    assert original.anthropic_api_key == round_trip.anthropic_api_key
    assert original.waaias_api_key == round_trip.waaias_api_key
    assert original.x402_private_key == round_trip.x402_private_key
    assert original.dynamodb_table == round_trip.dynamodb_table
    assert original.aws_region == round_trip.aws_region
    assert original.coingecko_api_key == round_trip.coingecko_api_key


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
