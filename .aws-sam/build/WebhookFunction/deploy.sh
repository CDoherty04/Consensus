#!/usr/bin/env bash
set -euo pipefail

# Auto-load .env.local (or whatever ENV_FILE points at) so you don't have to
# remember `set -a; source .env.local; set +a` every time.
ENV_FILE="${ENV_FILE:-.env.local}"
if [[ -f "$ENV_FILE" ]]; then
  echo "Loading env from $ENV_FILE"
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

STACK_NAME="${STACK_NAME:-telegram-ai-finance-bot}"
REGION="${AWS_REGION:-us-east-1}"
WALLET_NETWORK="${WALLET_NETWORK:-base-sepolia}"

required_vars=(
  TELEGRAM_TOKEN
)

for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "Missing required environment variable: $var" >&2
    exit 1
  fi
done

command -v sam >/dev/null || { echo "sam CLI not found on PATH" >&2; exit 1; }
command -v aws >/dev/null || { echo "aws CLI not found on PATH" >&2; exit 1; }

echo "Building SAM app..."
# Use a Lambda-matching container if Docker is available; otherwise fall back
# to a host-mode build (which requires python3.12 on PATH).
if docker info >/dev/null 2>&1; then
  sam build --use-container
else
  sam build
fi

echo "Deploying stack: $STACK_NAME (region=$REGION, network=$WALLET_NETWORK)"
sam deploy \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset \
  --parameter-overrides \
    TelegramToken="$TELEGRAM_TOKEN" \
    AnthropicApiKey="${ANTHROPIC_API_KEY:-}" \
    CoingeckoApiKey="${COINGECKO_API_KEY:-}" \
    WalletNetwork="$WALLET_NETWORK"

WEBHOOK_URL="$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='WebhookUrl'].OutputValue" \
  --output text)"

KMS_ALIAS="$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='WalletKmsKeyAlias'].OutputValue" \
  --output text)"

if [[ -n "$WEBHOOK_URL" ]]; then
  echo "Setting Telegram webhook to: $WEBHOOK_URL"
  curl -sS "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook?url=${WEBHOOK_URL}" >/dev/null
  echo "Webhook configured."
else
  echo "Failed to retrieve webhook URL output." >&2
  exit 1
fi

echo
echo "Deployment completed."
echo "  Webhook URL : $WEBHOOK_URL"
echo "  KMS alias   : $KMS_ALIAS"
echo
echo "Try the standalone wallet demo:"
echo "  export AWS_REGION=$REGION"
echo "  export DYNAMODB_TABLE=agent_bot_users"
echo "  export WALLET_KMS_KEY_ID=$KMS_ALIAS"
echo "  export WALLET_NETWORK=$WALLET_NETWORK"
echo "  python demo.py --user-id demo-user-001"
