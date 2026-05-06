"""
Configuration module for Telegram AI Finance Bot.

This module provides configuration parsing and validation for the bot,
loading settings from environment variables.
"""

import os
from dataclasses import dataclass
from typing import List


@dataclass
class Configuration:
    """
    Configuration object containing all required environment variables
    for the Telegram AI Finance Bot.
    
    Attributes:
        telegram_token: Bot authentication token from Telegram
        anthropic_api_key: API key for Claude AI
        waaias_api_key: API key for Wallet-as-a-Service
        x402_private_key: Private key for x402 protocol transactions
        dynamodb_table: Name of the DynamoDB table for state storage
        aws_region: AWS region for DynamoDB and other services
        coingecko_api_key: API key for CoinGecko price data
    """
    telegram_token: str
    anthropic_api_key: str
    waaias_api_key: str
    x402_private_key: str
    dynamodb_table: str
    aws_region: str
    coingecko_api_key: str
    
    @classmethod
    def from_env(cls) -> 'Configuration':
        """
        Load configuration from environment variables.
        
        Returns:
            Configuration: Configuration object populated from environment
            
        Raises:
            KeyError: If a required environment variable is missing
        """
        return cls(
            telegram_token=os.environ['TELEGRAM_TOKEN'],
            anthropic_api_key=os.environ['ANTHROPIC_API_KEY'],
            waaias_api_key=os.environ['WAAIAS_API_KEY'],
            x402_private_key=os.environ['X402_PRIVATE_KEY'],
            dynamodb_table=os.environ['DYNAMODB_TABLE'],
            aws_region=os.environ['AWS_REGION'],
            coingecko_api_key=os.environ['COINGECKO_API_KEY']
        )
    
    def validate(self) -> List[str]:
        """
        Validate configuration values and return any errors.
        
        Checks that all required fields are non-empty strings and that
        certain fields meet format requirements.
        
        Returns:
            List[str]: List of validation error messages. Empty list if valid.
        """
        errors = []
        
        # Check that all fields are non-empty strings
        if not self.telegram_token or not isinstance(self.telegram_token, str):
            errors.append("telegram_token must be a non-empty string")
        
        if not self.anthropic_api_key or not isinstance(self.anthropic_api_key, str):
            errors.append("anthropic_api_key must be a non-empty string")
        
        if not self.waaias_api_key or not isinstance(self.waaias_api_key, str):
            errors.append("waaias_api_key must be a non-empty string")
        
        if not self.x402_private_key or not isinstance(self.x402_private_key, str):
            errors.append("x402_private_key must be a non-empty string")
        
        if not self.dynamodb_table or not isinstance(self.dynamodb_table, str):
            errors.append("dynamodb_table must be a non-empty string")
        
        if not self.aws_region or not isinstance(self.aws_region, str):
            errors.append("aws_region must be a non-empty string")
        
        if not self.coingecko_api_key or not isinstance(self.coingecko_api_key, str):
            errors.append("coingecko_api_key must be a non-empty string")
        
        # Additional format validations
        if self.telegram_token and ':' not in self.telegram_token:
            errors.append("telegram_token appears to be invalid (should contain ':')")
        
        if self.x402_private_key and self.x402_private_key.startswith('0x'):
            # Private keys should typically be hex strings, optionally with 0x prefix
            if len(self.x402_private_key) not in [64, 66]:  # 64 hex chars or 66 with 0x
                errors.append("x402_private_key appears to be invalid length")
        
        return errors
