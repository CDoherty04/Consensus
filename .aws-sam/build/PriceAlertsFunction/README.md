# Telegram AI Finance Bot

Personal Telegram finance agent with dual interaction modes:
- **Menu Mode**: paginated inline keyboard UX
- **AI Mode**: natural language intent parsing with Claude tool use

It uses:
- x402 protocol on Base for value transfer and micropayments
- WAIaaS for managed wallet lifecycle
- AWS Lambda + API Gateway + DynamoDB for serverless infra
- EventBridge-scheduled workers for alerts, recurring payments, and feed digests

## Project Layout

- `handler.py` webhook Lambda entry point
- `bot/pages.py` menu rendering and page keyboard builders
- `bot/nl_mode.py` Claude tool definitions + parser fallback
- `bot/wallet_service.py` wallet/balance/transfer/swap/content helpers
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
- `WAAIAS_API_KEY`
- `X402_PRIVATE_KEY`
- `DYNAMODB_TABLE`
- `AWS_REGION`
- `COINGECKO_API_KEY` (optional but recommended)

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

## References

- [x402](https://x402.org)
- [WAIaaS](https://github.com/minhoyoo-iotrust/WAIaaS)
- [Base docs](https://docs.base.org/)
- [Anthropic Claude API](https://docs.anthropic.com/)
