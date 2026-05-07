#!/usr/bin/env python3
"""End-to-end demo of the AWS-backed wallet + x402 client.

What it shows:

    1. A fresh secp256k1 wallet is generated for a fake telegram user.
    2. The private key is encrypted with AWS KMS and the ciphertext is
       persisted to DynamoDB. Plaintext never leaves Lambda memory.
    3. We query the live Base Sepolia RPC for the wallet's ETH and USDC
       balances.
    4. If the wallet is funded (use https://faucets.chain.link or
       https://www.alchemy.com/faucets/base-sepolia), we sign + broadcast
       a real on-chain transfer.
    5. We attempt an x402 paywalled fetch against the public x402.org
       demo endpoint, which automatically settles the 402 challenge with
       USDC.

Required environment:
    AWS_REGION=us-east-1                  # any region where you have a key
    WALLET_KMS_KEY_ID=alias/agent-bot-wallet
    DYNAMODB_TABLE=agent_bot_users
    WALLET_NETWORK=base-sepolia           # default

Optional:
    DEMO_USER_ID=demo-user-001            # so re-runs reuse the same wallet
    DEMO_RECIPIENT=0x...                  # if set, a tiny ETH transfer is sent
    DEMO_PAYWALL_URL=https://...          # any x402-protected URL

Run:
    python demo.py
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from bot.db.user_state import UserStateDB
from bot.utils.coingecko_client import CoinGeckoClient
from bot.wallet.aws_wallet import AWSWallet, NETWORKS
from bot.wallet.x402_client import X402Client
from bot.wallet_service import WalletService


def _h(text: str) -> None:
    bar = "─" * 70
    print(f"\n{bar}\n  {text}\n{bar}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user-id", default=os.getenv("DEMO_USER_ID", "demo-user-001")
    )
    parser.add_argument("--recipient", default=os.getenv("DEMO_RECIPIENT"))
    parser.add_argument(
        "--amount-eth", type=float, default=float(os.getenv("DEMO_AMOUNT_ETH", "0.0001"))
    )
    parser.add_argument(
        "--paywall-url",
        default=os.getenv("DEMO_PAYWALL_URL", ""),
        help="An x402-protected URL to fetch (e.g. https://x402.org/protected)",
    )
    parser.add_argument(
        "--network",
        default=os.getenv("WALLET_NETWORK", "base-sepolia"),
        choices=list(NETWORKS),
    )
    args = parser.parse_args()

    table = os.getenv("DYNAMODB_TABLE", "agent_bot_users")
    region = os.getenv("AWS_REGION", "us-east-1")

    _h(f"DEMO: AWS-backed agent wallet on {args.network}")
    print(f"  region            : {region}")
    print(f"  dynamodb table    : {table}")
    print(f"  kms key           : {os.getenv('WALLET_KMS_KEY_ID', '(unset!)')}")

    user_db = UserStateDB(table, region=region)
    aws_wallet = AWSWallet(user_db=user_db, network=args.network)
    x402 = X402Client(wallet=aws_wallet)
    wallet = WalletService(
        aws_wallet=aws_wallet,
        x402_client=x402,
        prices_client=CoinGeckoClient(os.getenv("COINGECKO_API_KEY")),
    )

    # ---------------------------------------------------------------- 1
    _h("1. Provision wallet (KMS encrypt + DynamoDB write)")
    address = wallet.ensure_wallet(args.user_id)
    print(f"  user_id           : {args.user_id}")
    print(f"  wallet address    : {address}")
    print(f"  explorer          : {aws_wallet.explorer}/address/{address}")

    # ---------------------------------------------------------------- 2
    _h("2. Fetch balances from live RPC")
    balances = aws_wallet.get_balances(address) or {}
    eth = balances.get("ETH", 0.0)
    usdc = balances.get("USDC", 0.0)
    print(f"  ETH               : {eth}")
    print(f"  USDC              : {usdc}")
    if eth == 0 and usdc == 0:
        print(
            "\n  ➜ Fund the wallet to exercise transfer + x402:\n"
            "    https://www.alchemy.com/faucets/base-sepolia\n"
            "    https://faucet.circle.com  (USDC)"
        )

    # ---------------------------------------------------------------- 3
    _h("3. Sign + broadcast on-chain transfer")
    if not args.recipient:
        print("  (skipped — set --recipient or DEMO_RECIPIENT to run)")
    elif eth < args.amount_eth:
        print(f"  (skipped — need >= {args.amount_eth} ETH; have {eth})")
    else:
        tx_hash = wallet.send(
            user_id=args.user_id,
            destination_address=args.recipient,
            amount=args.amount_eth,
            currency="ETH",
        )
        print(f"  tx_hash           : {tx_hash}")
        print(f"  explorer          : {x402.get_explorer_url(tx_hash)}")

    # ---------------------------------------------------------------- 4
    _h("4. x402 paywalled fetch")
    if not args.paywall_url:
        print("  (skipped — set --paywall-url or DEMO_PAYWALL_URL)")
    elif usdc <= 0:
        print("  (skipped — wallet has no USDC for x402 settlement)")
    else:
        try:
            content = wallet.fetch_article(
                user_id=args.user_id,
                url=args.paywall_url,
                max_amount_usdc=0.10,
            )
            preview = content[:400].replace("\n", " ")
            print(f"  fetched {len(content)} chars")
            print(f"  preview           : {preview}…")
        except Exception as exc:
            print(f"  ❌ fetch failed     : {exc}")

    _h("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
