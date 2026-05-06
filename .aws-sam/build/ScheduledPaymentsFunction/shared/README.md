# Shared Module

This directory contains shared utilities and configuration used across multiple Lambda functions in the Telegram AI Finance Bot.

## Configuration Module

The `config.py` module provides configuration parsing and validation for the bot.

### Features

- **Environment Variable Loading**: Load configuration from environment variables using `Configuration.from_env()`
- **Validation**: Validate configuration values with descriptive error messages
- **Type Safety**: Uses Python dataclasses for type-safe configuration
- **All Required Fields**: Includes all 7 required environment variables

### Required Environment Variables

The Configuration module requires the following environment variables:

| Variable | Description |
|----------|-------------|
| `TELEGRAM_TOKEN` | Bot authentication token from Telegram (format: `123456:ABC-DEF...`) |
| `ANTHROPIC_API_KEY` | API key for Claude AI |
| `WAAIAS_API_KEY` | API key for Wallet-as-a-Service |
| `X402_PRIVATE_KEY` | Private key for x402 protocol transactions (64 hex chars, optionally with `0x` prefix) |
| `DYNAMODB_TABLE` | Name of the DynamoDB table for state storage |
| `AWS_REGION` | AWS region for DynamoDB and other services |
| `COINGECKO_API_KEY` | API key for CoinGecko price data |

### Usage

```python
from config import Configuration

# Load from environment variables
config = Configuration.from_env()

# Validate configuration
errors = config.validate()
if errors:
    for error in errors:
        print(f"Configuration error: {error}")
else:
    print("Configuration is valid!")

# Access configuration values
print(f"DynamoDB Table: {config.dynamodb_table}")
print(f"AWS Region: {config.aws_region}")
```

### Direct Instantiation

You can also create a Configuration object directly:

```python
config = Configuration(
    telegram_token='123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11',
    anthropic_api_key='sk-ant-api-key',
    waaias_api_key='waaias-api-key',
    x402_private_key='0x' + 'a' * 64,
    dynamodb_table='telegram-bot-users',
    aws_region='us-east-1',
    coingecko_api_key='cg-api-key'
)
```

### Validation

The `validate()` method checks:

- All fields are non-empty strings
- Telegram token contains a colon (`:`)
- x402 private key is the correct length (64 or 66 characters with `0x` prefix)

Returns a list of error messages (empty list if valid).

### Testing

Run the test suite:

```bash
python3 -m pytest shared/ -v
```

Run the example script:

```bash
python3 shared/example_usage.py
```

### Requirements Satisfied

This module satisfies the following requirements from the specification:

- **36.1**: Parse configuration into Configuration object
- **36.2**: Return descriptive error for invalid configuration
- **36.5**: Include all required environment variables

## Files

- `config.py` - Configuration dataclass and loading logic
- `test_config.py` - Unit tests for Configuration module
- `test_integration.py` - Integration tests verifying requirements
- `example_usage.py` - Example usage demonstration
- `__init__.py` - Package initialization
- `README.md` - This file
