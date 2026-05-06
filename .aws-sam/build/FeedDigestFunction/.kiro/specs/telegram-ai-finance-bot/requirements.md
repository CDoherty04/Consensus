# Requirements Document

## Introduction

The Telegram AI Finance Bot is a personal AI finance agent interface that enables users to manage cryptocurrency wallets, execute payments, invest in assets, access paywalled content, and interact with blockchain-based financial services through both a paginated menu interface and natural language commands powered by Claude AI. The bot integrates the x402 payment protocol on Base blockchain, AWS infrastructure for scalability, and WAIaaS (Wallet-as-a-Service) for agent wallet management.

## Glossary

- **Bot**: The Telegram AI Finance Bot system
- **User**: A Telegram user interacting with the Bot
- **Agent_Wallet**: The cryptocurrency wallet managed by WAIaaS for each User
- **Menu_Mode**: The paginated inline keyboard navigation interface
- **NL_Mode**: Natural language command mode powered by Claude AI
- **x402_Protocol**: The payment protocol used for blockchain transactions on Base
- **WAIaaS**: Wallet-as-a-Service provided by OpenClaw for agent wallet management
- **Contact**: A saved wallet address with an associated name in the User's contact list
- **Scheduled_Payment**: A recurring or one-time future payment configured by the User
- **Price_Alert**: A notification trigger when an asset reaches a specified price threshold
- **Feed_Subscription**: A saved RSS or newsletter URL for automated content fetching
- **DynamoDB_Store**: AWS DynamoDB table storing User state and configuration
- **Claude_API**: Anthropic Claude API for natural language processing
- **Page**: A distinct screen in Menu_Mode with specific functionality
- **Confirmation_Flow**: A two-step process requiring User approval before executing financial actions

## Requirements

### Requirement 1: Dual Interaction Modes

**User Story:** As a User, I want to interact with the Bot using either a menu interface or natural language commands, so that I can choose the interaction style that suits my preference and context.

#### Acceptance Criteria

1. WHEN a User sends /start or /menu, THE Bot SHALL activate Menu_Mode and display Page 0
2. WHEN a User taps the [🧠 AI Mode] button, THE Bot SHALL activate NL_Mode and store the mode preference in DynamoDB_Store
3. WHILE in NL_Mode, THE Bot SHALL display a [📋 Menu Mode] button
4. WHEN a User taps the [📋 Menu Mode] button, THE Bot SHALL activate Menu_Mode and restore the last viewed Page
5. THE DynamoDB_Store SHALL persist the User's active mode as either "menu" or "nl"

### Requirement 2: Menu Navigation System

**User Story:** As a User, I want to navigate through different pages of functionality using inline keyboard buttons, so that I can access all Bot features in an organized manner.

#### Acceptance Criteria

1. THE Bot SHALL provide exactly 5 Pages numbered 0 through 4
2. WHEN a User taps [→ Next], THE Bot SHALL display the next Page in sequence
3. WHEN a User taps [← Back], THE Bot SHALL display the previous Page in sequence
4. WHEN a User is on Page 0 and taps [← Back], THE Bot SHALL remain on Page 0
5. WHEN a User is on Page 4 and taps [→ Next], THE Bot SHALL remain on Page 4
6. THE Bot SHALL display the current page number as "Page X/5" on every Page
7. THE Bot SHALL render page transitions by editing the existing message in-place using editMessageText and editMessageReplyMarkup
8. THE Bot SHALL display a [🧠 AI Mode] button on every Page
9. THE DynamoDB_Store SHALL persist the User's current_page value

### Requirement 3: Agent Wallet Management

**User Story:** As a User, I want the Bot to manage a cryptocurrency wallet on my behalf, so that I can store and transact with digital assets without managing private keys directly.

#### Acceptance Criteria

1. WHEN a new User first interacts with the Bot, THE Bot SHALL create an Agent_Wallet via WAIaaS
2. THE Bot SHALL store the Agent_Wallet address in DynamoDB_Store associated with the User's telegram_user_id
3. WHEN a User requests their wallet address, THE Bot SHALL retrieve and display the Agent_Wallet address
4. THE Agent_Wallet SHALL support ETH and USDC on Base blockchain
5. THE Bot SHALL retrieve Agent_Wallet balance via WAIaaS API for both ETH and USDC
6. WHEN displaying balance, THE Bot SHALL include USD equivalent values

### Requirement 4: View Balance Functionality

**User Story:** As a User, I want to view my Agent_Wallet balance, so that I know how much cryptocurrency I have available.

#### Acceptance Criteria

1. WHEN a User taps [💰 View Balance] on Page 0, THE Bot SHALL fetch the Agent_Wallet ETH balance via WAIaaS
2. WHEN a User taps [💰 View Balance] on Page 0, THE Bot SHALL fetch the Agent_Wallet USDC balance via WAIaaS
3. THE Bot SHALL display both ETH and USDC balances with their USD equivalent values
4. IF the WAIaaS API request fails, THEN THE Bot SHALL send an error message to the User

### Requirement 5: Transaction History

**User Story:** As a User, I want to view my recent transactions, so that I can track my financial activity.

#### Acceptance Criteria

1. WHEN a User taps [📋 Transaction History] on Page 0, THE Bot SHALL retrieve the last 10 transactions from the Agent_Wallet
2. THE Bot SHALL display each transaction with amount, counterparty address, timestamp, and transaction type
3. THE Bot SHALL format timestamps in a human-readable format
4. IF there are no transactions, THEN THE Bot SHALL display "No transactions yet"

### Requirement 6: Add Funds

**User Story:** As a User, I want to deposit cryptocurrency into my Agent_Wallet, so that I can fund my account.

#### Acceptance Criteria

1. WHEN a User taps [➕ Add Funds] on Page 0, THE Bot SHALL display the Agent_Wallet address
2. THE Bot SHALL generate and display a QR code containing the Agent_Wallet address
3. THE Bot SHALL include instructions for depositing ETH or USDC on Base network

### Requirement 7: Withdraw Funds

**User Story:** As a User, I want to withdraw cryptocurrency from my Agent_Wallet to an external address, so that I can move funds to other wallets.

#### Acceptance Criteria

1. WHEN a User taps [➖ Withdraw Funds] on Page 0, THE Bot SHALL prompt the User for a destination address
2. WHEN the User provides a destination address, THE Bot SHALL prompt for an amount
3. WHEN the User provides an amount, THE Bot SHALL display a confirmation message with destination address and amount
4. WHEN the User confirms, THE Bot SHALL execute the withdrawal via x402_Protocol on Base
5. IF the withdrawal fails, THEN THE Bot SHALL send an error message to the User
6. WHEN the withdrawal succeeds, THE Bot SHALL send a success message with transaction hash

### Requirement 8: Token Swap

**User Story:** As a User, I want to swap one cryptocurrency for another, so that I can rebalance my portfolio.

#### Acceptance Criteria

1. WHEN a User taps [🔄 Swap Tokens] on Page 0, THE Bot SHALL display an inline keyboard of supported tokens for the FROM selection
2. WHEN the User selects a FROM token, THE Bot SHALL display an inline keyboard of supported tokens for the TO selection
3. WHEN the User selects a TO token, THE Bot SHALL prompt for an amount
4. WHEN the User provides an amount, THE Bot SHALL display a confirmation message with FROM token, TO token, amount, and estimated output
5. WHEN the User confirms, THE Bot SHALL execute the swap via x402_Protocol on Base
6. THE Bot SHALL support swapping between ETH, USDC, BTC, and SOL
7. IF the swap fails, THEN THE Bot SHALL send an error message to the User

### Requirement 9: Contact Management

**User Story:** As a User, I want to save wallet addresses with friendly names, so that I can easily send payments to frequent recipients.

#### Acceptance Criteria

1. WHEN a User taps [➕ Add Contact] on Page 1, THE Bot SHALL prompt for a contact name
2. WHEN the User provides a name, THE Bot SHALL prompt for a wallet address
3. WHEN the User provides a wallet address, THE Bot SHALL validate the address format
4. WHEN the address is valid, THE Bot SHALL save the Contact to DynamoDB_Store
5. IF the address is invalid, THEN THE Bot SHALL send an error message and re-prompt
6. WHEN a User taps [👥 View Contacts] on Page 1, THE Bot SHALL display a paginated list of saved Contacts
7. THE Bot SHALL display a [Remove] button inline with each Contact
8. WHEN a User taps [Remove] for a Contact, THE Bot SHALL delete the Contact from DynamoDB_Store

### Requirement 10: Send Money

**User Story:** As a User, I want to send cryptocurrency to my saved contacts, so that I can make payments quickly.

#### Acceptance Criteria

1. WHEN a User taps [📤 Send Money] on Page 1, THE Bot SHALL display an inline keyboard of all saved Contacts
2. WHEN the User selects a Contact, THE Bot SHALL prompt for an amount and currency
3. WHEN the User provides an amount and currency, THE Bot SHALL display a confirmation message with Contact name, amount, and currency
4. WHEN the User confirms, THE Bot SHALL execute the transfer via x402_Protocol on Base
5. IF the transfer fails, THEN THE Bot SHALL send an error message to the User
6. WHEN the transfer succeeds, THE Bot SHALL send a success message with transaction hash
7. THE Bot SHALL support sending ETH and USDC

### Requirement 11: Schedule Payment

**User Story:** As a User, I want to schedule recurring or one-time future payments, so that I can automate regular transactions.

#### Acceptance Criteria

1. WHEN a User taps [⏰ Schedule Payment] on Page 1, THE Bot SHALL display an inline keyboard of all saved Contacts
2. WHEN the User selects a Contact, THE Bot SHALL prompt for an amount and currency
3. WHEN the User provides an amount and currency, THE Bot SHALL prompt for recurrence with options: once, daily, weekly, monthly
4. WHEN the User selects recurrence, THE Bot SHALL save the Scheduled_Payment to DynamoDB_Store with a unique payment_id
5. THE Scheduled_Payment SHALL include Contact, amount, currency, recurrence, and next_run timestamp
6. WHEN a User taps [📅 Upcoming Payments] on Page 1, THE Bot SHALL display all Scheduled_Payments
7. THE Bot SHALL display a [Cancel] button inline with each Scheduled_Payment
8. WHEN a User taps [Cancel] for a Scheduled_Payment, THE Bot SHALL delete the Scheduled_Payment from DynamoDB_Store

### Requirement 12: Scheduled Payment Execution

**User Story:** As a User, I want my scheduled payments to execute automatically at the specified times, so that I don't have to manually trigger recurring transactions.

#### Acceptance Criteria

1. THE scheduled-payment-runner Lambda SHALL execute every hour
2. WHEN the scheduled-payment-runner executes, THE scheduled-payment-runner SHALL query DynamoDB_Store for all Scheduled_Payments where next_run is in the past
3. FOR ALL due Scheduled_Payments, THE scheduled-payment-runner SHALL execute the payment via x402_Protocol on Base
4. WHEN a Scheduled_Payment executes successfully, THE scheduled-payment-runner SHALL update next_run based on recurrence
5. WHEN a Scheduled_Payment with recurrence "once" executes successfully, THE scheduled-payment-runner SHALL delete the Scheduled_Payment from DynamoDB_Store
6. IF a Scheduled_Payment execution fails, THEN THE scheduled-payment-runner SHALL send a Telegram notification to the User
7. WHEN a Scheduled_Payment executes successfully, THE scheduled-payment-runner SHALL send a Telegram confirmation to the User

### Requirement 13: Request Money

**User Story:** As a User, I want to generate a payment request link, so that I can share it with others to request payment.

#### Acceptance Criteria

1. WHEN a User taps [🧾 Request Money] on Page 1, THE Bot SHALL prompt for an amount and currency
2. WHEN the User provides an amount and currency, THE Bot SHALL prompt for an optional memo
3. WHEN the User provides or skips the memo, THE Bot SHALL generate a payment request link containing the Agent_Wallet address, amount, currency, and memo
4. THE Bot SHALL send the payment request link to the User in a copy-friendly format

### Requirement 14: Buy Asset

**User Story:** As a User, I want to purchase cryptocurrency or tokenized assets, so that I can invest in digital assets.

#### Acceptance Criteria

1. WHEN a User taps [🛒 Buy Asset] on Page 2, THE Bot SHALL display an inline keyboard of supported assets: ETH, BTC, SOL, USDC, SPY, QQQ
2. WHEN the User selects an asset, THE Bot SHALL prompt for an amount in USD
3. WHEN the User provides an amount, THE Bot SHALL display a confirmation message with asset symbol and USD amount
4. WHEN the User confirms, THE Bot SHALL execute the purchase via on-chain swap or brokerage API
5. IF the purchase fails, THEN THE Bot SHALL send an error message to the User
6. WHEN the purchase succeeds, THE Bot SHALL send a success message with transaction details

### Requirement 15: Portfolio Summary

**User Story:** As a User, I want to view a summary of my investment holdings, so that I can track my portfolio performance.

#### Acceptance Criteria

1. WHEN a User taps [📊 Portfolio Summary] on Page 2, THE Bot SHALL retrieve all asset holdings from the Agent_Wallet
2. THE Bot SHALL display each asset with current quantity, cost basis, current value, and profit/loss
3. THE Bot SHALL calculate and display total portfolio value in USD
4. THE Bot SHALL calculate and display total profit/loss percentage

### Requirement 16: Price Alert Management

**User Story:** As a User, I want to set price alerts for assets, so that I am notified when an asset reaches my target price.

#### Acceptance Criteria

1. WHEN a User taps [🔔 Set Price Alert] on Page 2, THE Bot SHALL display an inline keyboard of supported assets
2. WHEN the User selects an asset, THE Bot SHALL prompt for a target price
3. WHEN the User provides a target price, THE Bot SHALL prompt for direction with options: Above, Below
4. WHEN the User selects a direction, THE Bot SHALL save the Price_Alert to DynamoDB_Store with a unique alert_id
5. WHEN a User taps [📉 View Alerts] on Page 2, THE Bot SHALL display all active Price_Alerts
6. THE Bot SHALL display a [Remove] button inline with each Price_Alert
7. WHEN a User taps [Remove] for a Price_Alert, THE Bot SHALL delete the Price_Alert from DynamoDB_Store

### Requirement 17: Price Alert Monitoring

**User Story:** As a User, I want to receive notifications when my price alerts are triggered, so that I can act on market movements.

#### Acceptance Criteria

1. THE price-alert-poller Lambda SHALL execute every 5 minutes
2. WHEN the price-alert-poller executes, THE price-alert-poller SHALL query DynamoDB_Store for all active Price_Alerts
3. FOR ALL active Price_Alerts, THE price-alert-poller SHALL fetch the current price from CoinGecko API
4. WHEN a Price_Alert with direction "Above" has current price greater than or equal to target price, THE price-alert-poller SHALL send a Telegram notification to the User
5. WHEN a Price_Alert with direction "Below" has current price less than or equal to target price, THE price-alert-poller SHALL send a Telegram notification to the User
6. WHEN a Price_Alert is triggered, THE price-alert-poller SHALL delete the Price_Alert from DynamoDB_Store
7. IF the CoinGecko API request fails, THEN THE price-alert-poller SHALL log the error and continue processing remaining alerts

### Requirement 18: Market Snapshot

**User Story:** As a User, I want to view recent price changes for assets in my portfolio, so that I can monitor market performance.

#### Acceptance Criteria

1. WHEN a User taps [📰 Market Snapshot] on Page 2, THE Bot SHALL retrieve all assets in the User's portfolio
2. FOR ALL portfolio assets, THE Bot SHALL fetch the 24-hour price change percentage from CoinGecko API
3. THE Bot SHALL display each asset with its symbol and 24-hour price change percentage
4. THE Bot SHALL format positive changes with a green indicator and negative changes with a red indicator

### Requirement 19: Fetch Paywalled Article

**User Story:** As a User, I want to access paywalled articles by having the Bot pay the x402 micropayment, so that I can read premium content without a subscription.

#### Acceptance Criteria

1. WHEN a User taps [🔓 Fetch Article] on Page 3, THE Bot SHALL prompt for an article URL
2. WHEN the User provides a URL, THE Bot SHALL validate the URL format
3. WHEN the URL is valid, THE Bot SHALL attempt to pay the x402 micropayment for the article
4. WHEN the payment succeeds, THE Bot SHALL retrieve the full article text
5. THE Bot SHALL chunk the article text into multiple Telegram messages if it exceeds message length limits
6. IF the payment or retrieval fails, THEN THE Bot SHALL send an error message to the User

### Requirement 20: Search Paywalled Articles

**User Story:** As a User, I want to search for articles on paywalled sources, so that I can discover relevant content before purchasing access.

#### Acceptance Criteria

1. WHEN a User taps [🔍 Search Articles] on Page 3, THE Bot SHALL prompt for a search topic
2. WHEN the User provides a topic, THE Bot SHALL search a paywalled source index for matching articles
3. THE Bot SHALL display article headlines with a [Fetch] button inline with each result
4. WHEN the User taps [Fetch] for an article, THE Bot SHALL execute the Fetch Paywalled Article flow for that article URL
5. IF the search fails, THEN THE Bot SHALL send an error message to the User

### Requirement 21: Feed Subscription Management

**User Story:** As a User, I want to subscribe to RSS feeds or newsletters, so that I can receive automated summaries of new content.

#### Acceptance Criteria

1. WHEN a User taps [📡 Subscribe to Feed] on Page 3, THE Bot SHALL prompt for an RSS or newsletter URL
2. WHEN the User provides a URL, THE Bot SHALL validate the URL format
3. WHEN the URL is valid, THE Bot SHALL save the Feed_Subscription to DynamoDB_Store with a unique subscription_id
4. THE Feed_Subscription SHALL include the URL and last_fetched timestamp
5. WHEN a User taps [📋 My Subscriptions] on Page 3, THE Bot SHALL display all active Feed_Subscriptions
6. THE Bot SHALL display an [Unsubscribe] button inline with each Feed_Subscription
7. WHEN a User taps [Unsubscribe] for a Feed_Subscription, THE Bot SHALL delete the Feed_Subscription from DynamoDB_Store

### Requirement 22: Feed Digest Generation

**User Story:** As a User, I want to receive daily summaries of new content from my subscribed feeds, so that I stay informed without manually checking each source.

#### Acceptance Criteria

1. THE feed-digest-runner Lambda SHALL execute daily at 8am UTC
2. WHEN the feed-digest-runner executes, THE feed-digest-runner SHALL query DynamoDB_Store for all Feed_Subscriptions
3. FOR ALL Feed_Subscriptions, THE feed-digest-runner SHALL fetch new content since last_fetched timestamp
4. WHEN new content is available, THE feed-digest-runner SHALL pay x402 micropayments for paywalled content
5. WHEN content is retrieved, THE feed-digest-runner SHALL summarize the content via Claude_API
6. THE feed-digest-runner SHALL send the summary to the User via Telegram
7. WHEN content is processed, THE feed-digest-runner SHALL update the last_fetched timestamp in DynamoDB_Store
8. IF content fetching or payment fails, THEN THE feed-digest-runner SHALL log the error and continue processing remaining subscriptions

### Requirement 23: Natural Language Command Processing

**User Story:** As a User, I want to control the Bot using natural language commands, so that I can interact conversationally without navigating menus.

#### Acceptance Criteria

1. WHILE in NL_Mode, WHEN a User sends a text message, THE Bot SHALL send the message to Claude_API with system prompt and conversation history
2. THE Bot SHALL provide Claude_API with tool definitions for all Bot commands
3. THE Bot SHALL include User's Agent_Wallet balance, Contact list, and available commands in the Claude_API system prompt
4. WHEN Claude_API returns a tool call, THE Bot SHALL map the tool call to the corresponding Bot action
5. THE Bot SHALL store the last 10 message turns in DynamoDB_Store for conversation context
6. IF Claude_API cannot determine User intent, THEN THE Bot SHALL send a helpful explanation message

### Requirement 24: Natural Language Confirmation Flow

**User Story:** As a User, I want to confirm financial actions initiated via natural language, so that I can prevent accidental transactions.

#### Acceptance Criteria

1. WHEN Claude_API returns a tool call for a financial action, THE Bot SHALL send a confirmation message to the User
2. THE confirmation message SHALL include the action type, recipient or asset, amount, and currency
3. THE Bot SHALL display [Yes] and [Cancel] buttons inline with the confirmation message
4. WHEN the User taps [Yes], THE Bot SHALL execute the financial action
5. WHEN the User taps [Cancel], THE Bot SHALL cancel the action and send a cancellation confirmation
6. Financial actions requiring confirmation SHALL include: send_money, withdraw_funds, buy_asset, swap_tokens, schedule_payment

### Requirement 25: Natural Language Tool Definitions

**User Story:** As a User, I want the Bot to support a comprehensive set of natural language commands, so that I can perform all Bot functions conversationally.

#### Acceptance Criteria

1. THE Bot SHALL provide Claude_API with tool definitions for: get_balance, get_transaction_history, add_funds, withdraw_funds, send_money, invest, fetch_article, set_price_alert, list_contacts, add_contact, remove_contact, schedule_payment, cancel_scheduled_payment, swap_tokens, get_portfolio_summary
2. WHEN a User says "send 5 USDC to Marcus", THE Bot SHALL map to send_money tool with contact_name="Marcus", amount=5, currency="USDC"
3. WHEN a User says "what's my balance", THE Bot SHALL map to get_balance tool
4. WHEN a User says "buy $20 of ETH", THE Bot SHALL map to invest tool with asset_symbol="ETH", amount=20
5. WHEN a User says "fetch this article: [url]", THE Bot SHALL map to fetch_article tool with url parameter
6. WHEN a User says "alert me when BTC hits 100k", THE Bot SHALL map to set_price_alert tool with asset_symbol="BTC", target_price=100000, direction="above"
7. WHEN a User says "pay Alex $10 every Friday", THE Bot SHALL map to schedule_payment tool with contact_name="Alex", amount=10, recurrence="weekly"
8. WHEN a User says "show me my last 5 transactions", THE Bot SHALL map to get_transaction_history tool with limit=5
9. WHEN a User says "swap all my USDC to ETH", THE Bot SHALL map to swap_tokens tool with from_token="USDC", to_token="ETH", amount=all

### Requirement 26: Network Selection

**User Story:** As a User, I want to switch between blockchain networks, so that I can use the Bot on different chains.

#### Acceptance Criteria

1. WHEN a User taps [🌐 Switch Network] on Page 4, THE Bot SHALL display an inline keyboard with options: Base Mainnet, Base Sepolia, Optimism
2. WHEN the User selects a network, THE Bot SHALL save the network preference to DynamoDB_Store
3. THE Bot SHALL use the selected network for all subsequent blockchain transactions
4. THE Bot SHALL display the currently selected network on Page 4

### Requirement 27: Wallet Address Display

**User Story:** As a User, I want to view my Agent_Wallet address, so that I can share it with others or verify my wallet.

#### Acceptance Criteria

1. WHEN a User taps [🪪 My Wallet Address] on Page 4, THE Bot SHALL display the Agent_Wallet address
2. THE Bot SHALL format the address in a copy-friendly format
3. THE Bot SHALL include a note indicating the current network

### Requirement 28: Private Key Export

**User Story:** As a User, I want to export my Agent_Wallet private key, so that I can import the wallet into other applications.

#### Acceptance Criteria

1. WHEN a User taps [🔐 Export Private Key] on Page 4, THE Bot SHALL display a confirmation prompt with a security warning
2. THE confirmation prompt SHALL include a [CONFIRM] button and a [Cancel] button
3. WHEN the User taps [CONFIRM], THE Bot SHALL retrieve the encrypted private key from WAIaaS
4. THE Bot SHALL display the encrypted private key with a security warning
5. WHEN the User taps [Cancel], THE Bot SHALL cancel the export and return to Page 4

### Requirement 29: Notification Preferences

**User Story:** As a User, I want to configure notification preferences, so that I can control which alerts I receive.

#### Acceptance Criteria

1. WHEN a User taps [🔔 Notification Prefs] on Page 4, THE Bot SHALL display toggle buttons for: price alerts, scheduled payment confirmations, feed digests
2. WHEN the User taps a toggle button, THE Bot SHALL update the preference in DynamoDB_Store
3. THE Bot SHALL display the current state of each toggle (on/off)
4. WHEN a notification preference is disabled, THE Bot SHALL not send notifications of that type to the User

### Requirement 30: Help Documentation

**User Story:** As a User, I want to access help documentation, so that I can learn how to use the Bot.

#### Acceptance Criteria

1. WHEN a User taps [❓ Help] on Page 4, THE Bot SHALL display a command reference
2. THE command reference SHALL include descriptions of all Bot commands
3. THE Bot SHALL include links to external documentation for x402_Protocol, WAIaaS, and Base blockchain

### Requirement 31: Error Handling for Failed Transactions

**User Story:** As a User, I want to receive clear error messages when transactions fail, so that I understand what went wrong and can take corrective action.

#### Acceptance Criteria

1. WHEN a blockchain transaction fails, THE Bot SHALL send an error message to the User
2. THE error message SHALL include the transaction type and reason for failure
3. IF the failure is due to insufficient balance, THEN THE Bot SHALL include the current balance in the error message
4. IF the failure is due to network issues, THEN THE Bot SHALL suggest retrying the transaction
5. THE Bot SHALL log all transaction failures for debugging purposes

### Requirement 32: Error Handling for API Timeouts

**User Story:** As a User, I want the Bot to handle API timeouts gracefully, so that temporary service disruptions don't break my workflow.

#### Acceptance Criteria

1. WHEN an API request to WAIaaS, Claude_API, CoinGecko, or x402_Protocol times out, THE Bot SHALL retry the request up to 3 times
2. IF all retry attempts fail, THEN THE Bot SHALL send an error message to the User
3. THE error message SHALL indicate that the service is temporarily unavailable
4. THE Bot SHALL log all API timeout errors for debugging purposes

### Requirement 33: Error Handling for Malformed User Input

**User Story:** As a User, I want the Bot to validate my input and provide helpful feedback, so that I can correct mistakes easily.

#### Acceptance Criteria

1. WHEN a User provides an invalid wallet address, THE Bot SHALL send an error message indicating the address format is invalid
2. WHEN a User provides an invalid amount (negative, zero, or non-numeric), THE Bot SHALL send an error message and re-prompt
3. WHEN a User provides an invalid URL, THE Bot SHALL send an error message indicating the URL format is invalid
4. WHEN a User provides an invalid asset symbol, THE Bot SHALL send an error message listing supported assets
5. THE Bot SHALL provide clear, friendly error messages for all validation failures

### Requirement 34: State Persistence

**User Story:** As a User, I want my Bot configuration and data to persist across sessions, so that I don't lose my settings or contacts.

#### Acceptance Criteria

1. THE DynamoDB_Store SHALL persist User state with primary key telegram_user_id
2. THE DynamoDB_Store SHALL store: current_page, interaction_mode, wallet_address, network, contacts, scheduled_payments, price_alerts, feed_subscriptions, nl_conversation_history
3. WHEN a User returns to the Bot after a period of inactivity, THE Bot SHALL restore the User's state from DynamoDB_Store
4. THE Bot SHALL handle DynamoDB read and write failures gracefully by logging errors and notifying the User

### Requirement 35: Webhook Handler

**User Story:** As a developer, I want the Bot to receive Telegram updates via webhook, so that the Bot can respond to User interactions in real-time.

#### Acceptance Criteria

1. THE Bot SHALL expose a webhook endpoint via AWS API Gateway
2. WHEN Telegram sends an update to the webhook, THE handler Lambda SHALL process the update
3. THE handler Lambda SHALL route callback queries to the appropriate page or action handler
4. THE handler Lambda SHALL route text messages to Menu_Mode or NL_Mode based on the User's current interaction_mode
5. THE handler Lambda SHALL respond to Telegram within 30 seconds to avoid timeout

### Requirement 36: Parser and Pretty Printer for Configuration

**User Story:** As a developer, I want to parse and format Bot configuration files, so that I can validate and display configuration settings.

#### Acceptance Criteria

1. WHEN a configuration file is provided, THE Config_Parser SHALL parse it into a Configuration object
2. WHEN an invalid configuration file is provided, THE Config_Parser SHALL return a descriptive error indicating the line and nature of the syntax error
3. THE Config_Pretty_Printer SHALL format Configuration objects back into valid configuration files
4. FOR ALL valid Configuration objects, parsing then printing then parsing SHALL produce an equivalent Configuration object (round-trip property)
5. THE Configuration object SHALL include all environment variables: TELEGRAM_TOKEN, ANTHROPIC_API_KEY, WAAIAS_API_KEY, X402_PRIVATE_KEY, DYNAMODB_TABLE, AWS_REGION, COINGECKO_API_KEY
