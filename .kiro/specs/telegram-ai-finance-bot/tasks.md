# Implementation Plan: Telegram AI Finance Bot

## Overview

This implementation plan breaks down the Telegram AI Finance Bot into discrete coding tasks following a serverless AWS architecture. The bot provides dual interaction modes (menu-based and natural language), cryptocurrency wallet management via WAIaaS, blockchain transactions via x402 protocol, and automated features like scheduled payments, price alerts, and content feed digests.

The implementation follows this structure:
- Core infrastructure setup (DynamoDB, Lambda configuration)
- Shared modules (database clients, API clients, utilities)
- Main webhook handler with menu mode pages
- Natural language mode with Claude integration
- Background Lambda functions for automation
- AWS SAM deployment configuration

## Tasks

- [x] 1. Set up project structure and shared modules
  - [x] 1.1 Create project directory structure and requirements files
    - Create root directory with subdirectories: `bot/`, `scheduler/`, `shared/`
    - Create `requirements.txt` for webhook handler dependencies
    - Create `scheduler/requirements.txt` for scheduler Lambda dependencies
    - Add dependencies: `boto3`, `requests`, `anthropic`, `python-telegram-bot`
    - _Requirements: 35.1, 35.2_

  - [x] 1.2 Implement Configuration module
    - Create `shared/config.py` with `Configuration` dataclass
    - Implement `from_env()` classmethod to load from environment variables
    - Implement `validate()` method to check required fields
    - Include fields: `telegram_token`, `anthropic_api_key`, `waaias_api_key`, `x402_private_key`, `dynamodb_table`, `aws_region`, `coingecko_api_key`
    - _Requirements: 36.1, 36.2, 36.5_

  - [x] 1.3 Implement DynamoDB client modules
    - Create `bot/db/user_state.py` with `UserStateDB` class
    - Implement methods: `get_user()`, `update_user()`, `create_user()`
    - Create `bot/db/contacts.py` with `ContactsDB` class
    - Implement methods: `add_contact()`, `get_contacts()`, `remove_contact()`
    - Create `bot/db/alerts.py` with `AlertsDB` class
    - Implement methods: `create_alert()`, `get_alerts()`, `get_all_active_alerts()`, `delete_alert()`
    - Create `bot/db/scheduled_payments.py` with `ScheduledPaymentsDB` class
    - Implement methods: `create_payment()`, `get_payments()`, `get_due_payments()`, `update_next_run()`, `delete_payment()`
    - Create `bot/db/subscriptions.py` with `SubscriptionsDB` class
    - Implement methods: `create_subscription()`, `get_subscriptions()`, `get_all_subscriptions()`, `update_last_fetched()`, `delete_subscription()`
    - _Requirements: 34.1, 34.2, 34.3, 34.4_

  - [x] 1.4 Implement validation and formatting utilities
    - Create `bot/utils/validation.py` with functions for validating wallet addresses, amounts, URLs, asset symbols
    - Create `bot/utils/formatting.py` with functions for formatting balances, timestamps, transaction details
    - Implement address format validation using regex for Ethereum addresses
    - Implement amount validation (positive, numeric)
    - Implement URL validation
    - _Requirements: 33.1, 33.2, 33.3, 33.4, 33.5_

- [ ] 2. Implement wallet and blockchain clients
  - [-] 2.1 Implement WAIaaS client
    - Create `bot/wallet/waaias_client.py` with `WAIaaSClient` class
    - Implement `create_wallet()` method to create new wallet via WAIaaS API
    - Implement `get_balance()` method to fetch ETH and USDC balances
    - Implement `get_transactions()` method to retrieve transaction history
    - Add retry logic with exponential backoff for API timeouts
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 32.1, 32.2, 32.3, 32.4_

  - [ ] 2.2 Implement x402 protocol client
    - Create `bot/wallet/x402_client.py` with `X402Client` class
    - Implement `send_transaction()` method for ETH/USDC transfers
    - Implement `swap_tokens()` method for token swaps
    - Implement `fetch_paywalled_content()` method for x402 micropayments
    - Add error handling for insufficient balance, network errors
    - _Requirements: 7.4, 7.5, 7.6, 8.5, 19.3, 19.4, 19.5, 19.6, 31.1, 31.2, 31.3, 31.4, 31.5_

  - [x] 2.3 Implement CoinGecko API client
    - Create `bot/utils/coingecko_client.py` with `CoinGeckoClient` class
    - Implement `get_price()` method to fetch current asset price
    - Implement `get_24h_change()` method to fetch 24-hour price change percentage
    - Add caching to reduce API calls
    - _Requirements: 17.3, 17.7, 18.2, 18.3, 18.4_

  - [x] 2.4 Implement Telegram API helper
    - Create `bot/utils/telegram.py` with helper functions
    - Implement `send_message()` function
    - Implement `edit_message()` function for in-place page updates
    - Implement `send_inline_keyboard()` function
    - Implement `answer_callback_query()` function
    - _Requirements: 2.7, 35.5_

- [~] 3. Checkpoint - Ensure shared modules are working
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Implement menu mode pages
  - [~] 4.1 Implement Page 0 - Wallet Operations
    - Create `bot/pages/page0.py` with `handle_page0_action()` function
    - Implement "view_balance" action: fetch and display ETH/USDC balances with USD values
    - Implement "tx_history" action: retrieve and format last 10 transactions
    - Implement "add_funds" action: display wallet address and QR code
    - Implement "withdraw" action: prompt for address and amount, show confirmation
    - Implement "swap" action: show token selection, prompt for amount, show confirmation
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 7.1, 7.2, 7.3, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [~] 4.2 Implement Page 1 - Contacts & Payments
    - Create `bot/pages/page1.py` with `handle_page1_action()` function
    - Implement "add_contact" action: prompt for name and address, validate and save
    - Implement "view_contacts" action: display paginated contact list with remove buttons
    - Implement "send_money" action: show contact selection, prompt for amount/currency, show confirmation
    - Implement "schedule_payment" action: show contact selection, prompt for amount/currency/recurrence, save to DB
    - Implement "view_scheduled" action: display scheduled payments with cancel buttons
    - Implement "request_money" action: prompt for amount/currency/memo, generate payment link
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 13.1, 13.2, 13.3, 13.4_

  - [~] 4.3 Implement Page 2 - Investments & Alerts
    - Create `bot/pages/page2.py` with `handle_page2_action()` function
    - Implement "buy_asset" action: show asset selection (ETH, BTC, SOL, USDC, SPY, QQQ), prompt for USD amount, show confirmation
    - Implement "portfolio" action: fetch holdings, calculate cost basis and P/L, display summary
    - Implement "set_alert" action: show asset selection, prompt for target price and direction, save to DB
    - Implement "view_alerts" action: display active alerts with remove buttons
    - Implement "market_snapshot" action: fetch portfolio assets, get 24h changes, format with indicators
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 15.1, 15.2, 15.3, 15.4, 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7, 18.1, 18.2, 18.3, 18.4_

  - [~] 4.4 Implement Page 3 - Content Access
    - Create `bot/pages/page3.py` with `handle_page3_action()` function
    - Implement "fetch_article" action: prompt for URL, validate, pay x402 micropayment, retrieve and chunk article text
    - Implement "search_articles" action: prompt for topic, search paywalled index, display results with fetch buttons
    - Implement "subscribe_feed" action: prompt for RSS/newsletter URL, validate and save to DB
    - Implement "view_subscriptions" action: display subscriptions with unsubscribe buttons
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 20.1, 20.2, 20.3, 20.4, 20.5, 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7_

  - [~] 4.5 Implement Page 4 - Settings
    - Create `bot/pages/page4.py` with `handle_page4_action()` function
    - Implement "switch_network" action: show network options (Base Mainnet, Base Sepolia, Optimism), save selection
    - Implement "show_address" action: display wallet address with network info
    - Implement "export_key" action: show security warning with confirm/cancel, retrieve and display encrypted private key
    - Implement "notification_prefs" action: display toggle buttons for price alerts, scheduled payments, feed digests
    - Implement "help" action: display command reference with links to external docs
    - _Requirements: 26.1, 26.2, 26.3, 26.4, 27.1, 27.2, 27.3, 28.1, 28.2, 28.3, 28.4, 28.5, 29.1, 29.2, 29.3, 29.4, 30.1, 30.2, 30.3_

  - [~] 4.6 Implement page navigation and state machine
    - Create `bot/pages/__init__.py` with `PAGE_DEFINITIONS` dictionary
    - Implement `get_next_page()` and `get_prev_page()` functions with boundary checking
    - Implement `render_page()` function to generate inline keyboard from page definition
    - Implement page routing logic to map actions to handler functions
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9_

- [~] 5. Checkpoint - Ensure menu mode pages are working
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement natural language mode
  - [~] 6.1 Implement Claude tool definitions
    - Create `bot/nl_mode/tools.py` with `CLAUDE_TOOLS` list
    - Define tool schemas for: `get_balance`, `get_transaction_history`, `send_money`, `withdraw_funds`, `swap_tokens`, `invest`, `set_price_alert`, `schedule_payment`, `fetch_article`, `add_contact`, `list_contacts`, `get_portfolio_summary`
    - Include proper input schemas with types, enums, and descriptions
    - _Requirements: 25.1, 25.2, 25.3, 25.4, 25.5, 25.6, 25.7, 25.8, 25.9_

  - [~] 6.2 Implement Claude API processor
    - Create `bot/nl_mode/processor.py` with `process_nl_message()` function
    - Build system prompt with user context (balance, contacts, available commands)
    - Send message to Claude API with tools and conversation history
    - Parse Claude response and extract tool calls
    - Store conversation turn in DynamoDB (last 10 turns)
    - _Requirements: 23.1, 23.2, 23.3, 23.4, 23.5, 23.6_

  - [~] 6.3 Implement tool call mapper
    - Create `bot/nl_mode/tool_mapper.py` with `execute_tool()` function
    - Map each tool name to corresponding bot action
    - Extract parameters from tool call and validate
    - Execute action and return result
    - Handle errors and return user-friendly messages
    - _Requirements: 23.4, 25.2, 25.3, 25.4, 25.5, 25.6, 25.7, 25.8, 25.9_

  - [~] 6.4 Implement confirmation flow for financial actions
    - Create `bot/nl_mode/confirmation.py` with `send_confirmation()` function
    - Identify financial actions requiring confirmation: send_money, withdraw_funds, buy_asset, swap_tokens, schedule_payment
    - Generate confirmation message with action details
    - Display [Yes] and [Cancel] inline buttons
    - Handle confirmation callback and execute action on [Yes]
    - _Requirements: 24.1, 24.2, 24.3, 24.4, 24.5, 24.6_

  - [~] 6.5 Implement mode switching
    - Add mode switching logic to handle [🧠 AI Mode] and [📋 Menu Mode] buttons
    - Update user state in DynamoDB when mode changes
    - Restore last viewed page when switching back to menu mode
    - Display appropriate mode button on all pages/messages
    - _Requirements: 1.2, 1.3, 1.4, 1.5_

- [ ] 7. Implement main webhook handler
  - [~] 7.1 Implement webhook handler entry point
    - Create `handler.py` with `lambda_handler()` function
    - Parse incoming Telegram update from API Gateway event
    - Route callback queries to page handlers or confirmation handlers
    - Route text messages to menu mode or NL mode based on user state
    - Initialize new users with wallet creation and default state
    - Return 200 response within 30 seconds
    - _Requirements: 1.1, 3.1, 3.2, 34.3, 35.1, 35.2, 35.3, 35.4, 35.5_

  - [~] 7.2 Implement error handling and logging
    - Add try-catch blocks around all external API calls
    - Log errors to CloudWatch with context (user_id, action, error message)
    - Send user-friendly error messages for common failures
    - Handle DynamoDB read/write failures gracefully
    - _Requirements: 31.1, 31.2, 31.3, 31.4, 31.5, 32.1, 32.2, 32.3, 32.4, 34.4_

- [~] 8. Checkpoint - Ensure webhook handler is working
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Implement scheduled payment runner Lambda
  - [~] 9.1 Implement payment execution logic
    - Create `scheduler/payments.py` with `lambda_handler()` function
    - Query DynamoDB for payments where `next_run <= now`
    - For each due payment, execute transaction via x402 client
    - On success: update `next_run` based on recurrence or delete if "once"
    - On failure: send error notification to user via Telegram
    - Send confirmation notification on successful execution
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_

  - [~] 9.2 Implement next_run calculation
    - Create helper function `calculate_next_run()` in `scheduler/payments.py`
    - Calculate next execution time based on recurrence: daily (+1 day), weekly (+7 days), monthly (+30 days)
    - Handle timezone conversions (store as UTC timestamps)
    - _Requirements: 12.4, 12.5_

- [ ] 10. Implement price alert poller Lambda
  - [~] 10.1 Implement alert checking logic
    - Create `scheduler/price_alerts.py` with `lambda_handler()` function
    - Query DynamoDB for all active price alerts
    - For each alert, fetch current price from CoinGecko
    - Compare current price with target price based on direction
    - If triggered: send Telegram notification and delete alert from DB
    - Handle CoinGecko API failures gracefully
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7_

  - [~] 10.2 Implement price comparison logic
    - Create `check_alert()` function in `scheduler/price_alerts.py`
    - For "above" direction: trigger if current_price >= target_price
    - For "below" direction: trigger if current_price <= target_price
    - Return boolean indicating whether alert should trigger
    - _Requirements: 17.4, 17.5_

- [ ] 11. Implement feed digest runner Lambda
  - [~] 11.1 Implement feed fetching logic
    - Create `scheduler/feed_digest.py` with `lambda_handler()` function
    - Query DynamoDB for all feed subscriptions
    - For each subscription, fetch new content since `last_fetched` timestamp
    - Parse RSS feeds and extract article titles, URLs, summaries
    - Pay x402 micropayments for paywalled content
    - _Requirements: 22.1, 22.2, 22.3, 22.4, 22.5, 22.8_

  - [~] 11.2 Implement content summarization
    - Create `summarize_content()` function in `scheduler/feed_digest.py`
    - Send content items to Claude API for summarization
    - Format summary with article titles, key points, and links
    - Chunk summary if it exceeds Telegram message length limit
    - _Requirements: 22.5, 22.6_

  - [~] 11.3 Implement digest delivery
    - Send formatted digest to user via Telegram
    - Update `last_fetched` timestamp in DynamoDB after successful processing
    - Handle failures gracefully and continue processing remaining subscriptions
    - _Requirements: 22.6, 22.7, 22.8_

- [ ] 12. Implement AWS SAM deployment configuration
  - [~] 12.1 Create SAM template
    - Create `template.yaml` with AWS SAM template
    - Define webhook-handler Lambda with API Gateway trigger
    - Define scheduled-payment-runner Lambda with EventBridge hourly rule
    - Define price-alert-poller Lambda with EventBridge 5-minute rule
    - Define feed-digest-runner Lambda with EventBridge daily 8am UTC rule
    - Define DynamoDB table with partition key `telegram_user_id`
    - Configure Lambda environment variables from SSM Parameter Store
    - Set Lambda timeout to 30 seconds for webhook handler, 5 minutes for schedulers
    - _Requirements: 35.1, 35.2, 35.3, 35.4, 35.5_

  - [~] 12.2 Create deployment script
    - Create `deploy.sh` script to build and deploy SAM application
    - Add commands to install dependencies in Lambda layers
    - Add SAM build and deploy commands with parameter overrides
    - Add script to set Telegram webhook URL after deployment
    - _Requirements: 35.1_

  - [~] 12.3 Create README with setup instructions
    - Create `README.md` with project overview
    - Document environment variables and how to configure them
    - Document deployment steps using `deploy.sh`
    - Document how to set up Telegram bot token
    - Include links to WAIaaS, x402, and CoinGecko API documentation
    - _Requirements: 30.3_

- [~] 13. Final checkpoint - Integration testing
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All Lambda functions are stateless with state persisted in DynamoDB
- Financial actions require explicit user confirmation via inline buttons
- External API calls include retry logic with exponential backoff
- Error messages are user-friendly and include actionable guidance
- Conversation history is limited to last 10 turns to manage context size
- Scheduled tasks use EventBridge for reliable triggering
- The bot supports ETH and USDC on Base blockchain via x402 protocol
- WAIaaS handles wallet creation and key management for security
- All timestamps are stored as Unix timestamps in UTC

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4", "2.3", "2.4"] },
    { "id": 2, "tasks": ["2.1", "2.2"] },
    { "id": 3, "tasks": ["4.1", "4.2", "4.3", "4.4", "4.5"] },
    { "id": 4, "tasks": ["4.6", "6.1"] },
    { "id": 5, "tasks": ["6.2", "6.3"] },
    { "id": 6, "tasks": ["6.4", "6.5"] },
    { "id": 7, "tasks": ["7.1", "7.2"] },
    { "id": 8, "tasks": ["9.1", "9.2", "10.1", "10.2", "11.1"] },
    { "id": 9, "tasks": ["11.2", "11.3"] },
    { "id": 10, "tasks": ["12.1", "12.2", "12.3"] }
  ]
}
```
