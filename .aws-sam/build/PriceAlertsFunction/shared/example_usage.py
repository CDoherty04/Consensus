"""
Example usage of the Configuration module.

This script demonstrates how to use the Configuration class to load
and validate bot configuration from environment variables.
"""

import os
from config import Configuration


def main():
    """Demonstrate Configuration usage"""
    
    print("=== Configuration Module Example ===\n")
    
    # Example 1: Load from environment variables
    print("1. Loading configuration from environment variables:")
    try:
        # Set example environment variables
        os.environ['TELEGRAM_TOKEN'] = '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'
        os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-api-key-example'
        os.environ['WAAIAS_API_KEY'] = 'waaias-api-key-example'
        os.environ['X402_PRIVATE_KEY'] = '0x' + 'a' * 64
        os.environ['DYNAMODB_TABLE'] = 'telegram-finance-bot-users'
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['COINGECKO_API_KEY'] = 'CG-api-key-example'
        
        config = Configuration.from_env()
        print(f"   ✓ Successfully loaded configuration")
        print(f"   - DynamoDB Table: {config.dynamodb_table}")
        print(f"   - AWS Region: {config.aws_region}")
        print(f"   - Telegram Token: {config.telegram_token[:10]}...")
        print()
    except KeyError as e:
        print(f"   ✗ Missing environment variable: {e}")
        print()
    
    # Example 2: Validate configuration
    print("2. Validating configuration:")
    errors = config.validate()
    if not errors:
        print("   ✓ Configuration is valid")
    else:
        print("   ✗ Configuration has errors:")
        for error in errors:
            print(f"     - {error}")
    print()
    
    # Example 3: Invalid configuration
    print("3. Testing invalid configuration:")
    invalid_config = Configuration(
        telegram_token='invalid-token',  # Missing colon
        anthropic_api_key='',  # Empty
        waaias_api_key='test',
        x402_private_key='0x123',  # Too short
        dynamodb_table='test-table',
        aws_region='',  # Empty
        coingecko_api_key='test'
    )
    
    errors = invalid_config.validate()
    print(f"   Found {len(errors)} validation errors:")
    for error in errors:
        print(f"     - {error}")
    print()
    
    # Example 4: Direct instantiation
    print("4. Creating configuration directly:")
    direct_config = Configuration(
        telegram_token='987654:XYZ-ABC9876fedcba-123',
        anthropic_api_key='sk-ant-direct-key',
        waaias_api_key='waaias-direct-key',
        x402_private_key='b' * 64,
        dynamodb_table='my-bot-table',
        aws_region='eu-west-1',
        coingecko_api_key='cg-direct-key'
    )
    print(f"   ✓ Created configuration with:")
    print(f"   - Table: {direct_config.dynamodb_table}")
    print(f"   - Region: {direct_config.aws_region}")
    print()
    
    print("=== Example Complete ===")


if __name__ == '__main__':
    main()
