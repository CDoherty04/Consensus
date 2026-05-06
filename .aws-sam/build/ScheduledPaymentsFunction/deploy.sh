#!/usr/bin/env bash
set -euo pipefail

STACK_NAME="${STACK_NAME:-telegram-ai-finance-bot}"
REGION="${AWS_REGION:-us-east-1}"

required_vars=(
  TELEGRAM_TOKEN
  ANTHROPIC_API_KEY
  WAAIAS_API_KEY
  X402_PRIVATE_KEY
)

for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "Missing required environment variable: $var" >&2
    exit 1
  fi
done

echo "Building SAM app..."
sam build

echo "Deploying stack: $STACK_NAME"
sam deploy \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset \
  --parameter-overrides \
    TelegramToken="$TELEGRAM_TOKEN" \
    AnthropicApiKey="$ANTHROPIC_API_KEY" \
    WaaiasApiKey="$WAAIAS_API_KEY" \
    X402PrivateKey="$X402_PRIVATE_KEY" \
    CoingeckoApiKey="${COINGECKO_API_KEY:-}"

WEBHOOK_URL="$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='WebhookUrl'].OutputValue" \
  --output text)"

if [[ -n "$WEBHOOK_URL" ]]; then
  echo "Setting Telegram webhook to: $WEBHOOK_URL"
  curl -sS "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook?url=${WEBHOOK_URL}" >/dev/null
  echo "Webhook configured."
else
  echo "Failed to retrieve webhook URL output." >&2
  exit 1
fi

echo "Deployment completed successfully."

