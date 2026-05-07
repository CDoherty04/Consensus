# Telegram AI Finance Bot

Personal Telegram finance agent with dual interaction modes:
- **Menu Mode**: paginated inline keyboard UX
- **AI Mode**: natural language intent parsing with Claude tool use

It uses:
- **x402 protocol** on Base / Base Sepolia for transfers and paywall micropayments
  (Coinbase x402 Python SDK + `eth_account` signing)
- **AWS-native non-custodial wallets**: each user's secp256k1 private key is
  generated on Lambda, encrypted under an AWS KMS CMK, and the ciphertext is
  stored in DynamoDB. Plaintext keys never touch disk or logs.
- **AWS Lambda + API Gateway + DynamoDB + KMS** for serverless infra
- EventBridge-scheduled workers for alerts, recurring payments, and feed digests

## Project Layout

- `handler.py` webhook Lambda entry point
- `bot/pages.py` menu rendering and page keyboard builders
- `bot/nl_mode.py` Claude tool definitions + parser fallback
- `bot/wallet/aws_wallet.py` KMS-backed wallet provisioning + on-chain reads
- `bot/wallet/x402_client.py` real EVM signing + x402 paywall settlement
- `bot/wallet_service.py` user-facing wallet/balance/transfer/swap/content helpers
- `demo.py` standalone end-to-end CLI demo on Base Sepolia
- `bot/contacts.py`, `bot/alerts.py`, `bot/scheduler.py`, `bot/feeds.py` domain services
- `bot/db/` DynamoDB data access modules
- `scheduler/payments.py` scheduled payment runner
- `scheduler/price_alerts.py` price alert poller
- `scheduler/feed_digest.py` feed digest runner
- `template.yaml` AWS SAM stack
- `deploy.sh` deployment + webhook registration script

## Environment Variables

Required:
- `TELEGRAM_TOKEN`
- `ANTHROPIC_API_KEY`
- `DYNAMODB_TABLE` (default `agent_bot_users`)
- `AWS_REGION`
- `WALLET_KMS_KEY_ID` — KMS key/alias used to encrypt user wallet keys
  (the SAM template provisions `alias/agent-bot-wallet` automatically)

Optional:
- `WALLET_NETWORK` — `base-sepolia` (default) | `base-mainnet` | `optimism`
- `COINGECKO_API_KEY`

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r scheduler/requirements.txt
```

## Run Tests

```bash
python3 -m pytest -q
```

## Deploy (AWS SAM)

1. Install AWS CLI + SAM CLI and configure AWS credentials.
2. Export required env vars.
3. Deploy:

```bash
chmod +x deploy.sh
./deploy.sh
```

`deploy.sh` builds and deploys the stack, then sets the Telegram webhook URL automatically.

## Telegram Usage

- `/start` or `/menu` opens menu mode.
- `🧠 AI Mode` switches to natural language mode.
- `📋 Menu Mode` returns to paginated UI.
- All money-moving actions require confirmation with `Yes`/`Cancel`.

## Notes

- User state is persisted in `agent_bot_users` DynamoDB table.
- NL conversation context stores the latest 10 turns.
- Scheduled workers are configured by `template.yaml` EventBridge rules:
  - every 5 minutes: price alerts
  - every hour: scheduled payments
  - daily at 08:00 UTC: feed digests

## Quick Demo

After `sam deploy` (or against any AWS account with a KMS key + DynamoDB
table you control):

```bash
export AWS_REGION=us-east-1
export DYNAMODB_TABLE=agent_bot_users
export WALLET_KMS_KEY_ID=alias/agent-bot-wallet
export WALLET_NETWORK=base-sepolia

# 1. Provision a wallet for a fake user, print the address.
python demo.py --user-id demo-user-001

# 2. Fund the printed address from a Base Sepolia faucet, then send a tx:
python demo.py --user-id demo-user-001 \
               --recipient 0xYourBurnerAddress \
               --amount-eth 0.0001

# 3. Settle a real x402 paywall in USDC:
python demo.py --user-id demo-user-001 \
               --paywall-url https://x402.org/protected
```

Every transaction is signed locally with `eth_account`, broadcast through
the Base RPC, and the explorer URL is printed for verification.

## References

- [x402](https://x402.org) — Coinbase payment protocol
- [x402 Python SDK](https://pypi.org/project/x402/)
- [Base docs](https://docs.base.org/)
- [AWS KMS Encrypt API](https://docs.aws.amazon.com/kms/latest/APIReference/API_Encrypt.html)
- [Anthropic Claude API](https://docs.anthropic.com/)
