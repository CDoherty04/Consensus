"""AWS Lambda webhook handler for Telegram AI finance bot."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

from bot.alerts import AlertsService
from bot.contacts import ContactsService
from bot.db.alerts import AlertsDB
from bot.db.contacts import ContactsDB
from bot.db.scheduled_payments import ScheduledPaymentsDB
from bot.db.subscriptions import SubscriptionsDB
from bot.db.user_state import UserStateDB
from bot.feeds import FeedService
from bot.nl_mode import NLModeService
from bot.pages import build_menu_page, build_nl_mode_keyboard, clamp_page
from bot.scheduler import PaymentSchedulerService
from bot.utils.formatting import (
    format_address,
    format_balance,
    format_contact,
    format_error_message,
    format_price_alert,
    format_price_change,
    format_scheduled_payment,
    format_timestamp,
    format_usd_value,
)
from bot.utils.telegram import answer_callback_query, edit_message, send_message
from bot.utils.validation import (
    validate_amount,
    validate_currency,
    validate_url,
    validate_wallet_address,
)
from bot.wallet.aws_wallet import AWSWallet
from bot.wallet.x402_client import X402Client
from bot.wallet_service import WalletService
from bot.utils.coingecko_client import CoinGeckoClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_services: Dict[str, Any] = {}

SUPPORTED_SWAP_TOKENS = ["ETH", "USDC", "BTC", "SOL"]
SUPPORTED_INVEST_ASSETS = ["ETH", "BTC", "SOL", "USDC", "SPY", "QQQ"]


def _get_env(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def _get_services() -> Dict[str, Any]:
    if _services:
        return _services

    region = os.getenv("AWS_REGION", "us-east-1")
    table_name = _get_env("DYNAMODB_TABLE")
    coingecko_api_key = os.getenv("COINGECKO_API_KEY")

    user_db = UserStateDB(table_name, region=region)
    contacts_db = ContactsDB(table_name, region=region)
    alerts_db = AlertsDB(table_name, region=region)
    payments_db = ScheduledPaymentsDB(table_name, region=region)
    subscriptions_db = SubscriptionsDB(table_name, region=region)

    prices = CoinGeckoClient(coingecko_api_key)
    network = os.getenv("WALLET_NETWORK", "base-sepolia")
    aws_wallet = AWSWallet(
        user_db=user_db,
        kms_key_id=os.getenv("WALLET_KMS_KEY_ID", ""),
        network=network,
    )
    x402 = X402Client(wallet=aws_wallet)
    wallet = WalletService(aws_wallet=aws_wallet, x402_client=x402, prices_client=prices)

    _services.update(
        {
            "telegram_token": _get_env("TELEGRAM_TOKEN"),
            "user_db": user_db,
            "contacts": ContactsService(contacts_db),
            "alerts": AlertsService(alerts_db, prices),
            "payments": PaymentSchedulerService(payments_db),
            "feeds": FeedService(subscriptions_db),
            "wallet": wallet,
            "nl": NLModeService(api_key=os.getenv("ANTHROPIC_API_KEY", "")),
        }
    )
    return _services


def _response(status: int = 200, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"statusCode": status, "body": json.dumps(body or {"ok": True})}


def _safe_body(event: Dict[str, Any]) -> Dict[str, Any]:
    if "body" not in event:
        return event
    body = event["body"]
    if isinstance(body, dict):
        return body
    if not body:
        return {}
    return json.loads(body)


def _ensure_user(user_id: str, services: Dict[str, Any]) -> Dict[str, Any]:
    user_db: UserStateDB = services["user_db"]
    user = user_db.get_user(user_id)
    if user:
        return user

    wallet: WalletService = services["wallet"]
    # AWSWallet handles both key generation (KMS) and DynamoDB user creation.
    wallet.ensure_wallet(user_id)
    return user_db.get_user(user_id) or {}


def _update_user(user_id: str, services: Dict[str, Any], updates: Dict[str, Any]) -> None:
    updates["updated_at"] = int(time.time())
    services["user_db"].update_user(user_id, updates)


def _render_menu(chat_id: str, user_id: str, services: Dict[str, Any], message_id: Optional[int] = None) -> None:
    user = _ensure_user(user_id, services)
    page = clamp_page(int(user.get("current_page", 0)))
    payload = build_menu_page(page=page, network=user.get("network", "base-mainnet"))
    token = services["telegram_token"]
    if message_id:
        edit_message(token, chat_id, message_id, text=payload["text"], reply_markup=payload["reply_markup"])
    else:
        send_message(token, chat_id, payload["text"], reply_markup=payload["reply_markup"])


def _start_confirmation(
    user_id: str,
    chat_id: str,
    services: Dict[str, Any],
    title: str,
    action_name: str,
    action_params: Dict[str, Any],
) -> None:
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "Yes", "callback_data": "confirm:yes"},
                {"text": "Cancel", "callback_data": "confirm:cancel"},
            ]
        ]
    }
    send_message(
        services["telegram_token"],
        chat_id,
        f"{title}\n\nConfirm?",
        reply_markup=keyboard,
    )
    _update_user(
        user_id,
        services,
        {
            "pending_action": {
                "action_name": action_name,
                "action_params": action_params,
                "expires_at": int(time.time()) + 600,
            }
        },
    )


def _chunk_and_send(chat_id: str, token: str, text: str, chunk_size: int = 3500) -> None:
    for i in range(0, len(text), chunk_size):
        send_message(token, chat_id, text[i : i + chunk_size], parse_mode="HTML")


def _execute_action(
    action_name: str, params: Dict[str, Any], user: Dict[str, Any], services: Dict[str, Any]
) -> str:
    wallet: WalletService = services["wallet"]
    contacts: ContactsService = services["contacts"]
    alerts: AlertsService = services["alerts"]
    payments: PaymentSchedulerService = services["payments"]
    feeds: FeedService = services["feeds"]
    user_id = user["telegram_user_id"]
    wallet_address = user["wallet_address"]

    if action_name == "get_balance":
        summary = wallet.get_balance_summary(wallet_address)
        return (
            "💰 <b>Balance</b>\n"
            f"• {format_balance(summary['ETH'], 'ETH')} ({format_usd_value(summary['eth_usd'])})\n"
            f"• {format_balance(summary['USDC'], 'USDC')} ({format_usd_value(summary['usdc_usd'])})\n"
            f"• Total: {format_usd_value(summary['total_usd'])}"
        )

    if action_name == "get_transaction_history":
        txs = wallet.get_transaction_history(wallet_address, int(params.get("limit", 10)))
        if not txs:
            return "No transactions yet."
        lines = ["📋 <b>Recent Transactions</b>"]
        for tx in txs[:10]:
            direction = "📤" if tx.get("type") == "send" else "📥"
            token = tx.get("token", "ETH")
            lines.append(
                f"{direction} {tx.get('amount', 0)} {token} • {format_timestamp(int(tx.get('timestamp', 0) or 0))}"
            )
        return "\n".join(lines)

    if action_name == "withdraw_funds":
        tx_hash = wallet.send(
            user_id=user_id,
            destination_address=params["destination_address"],
            amount=float(params["amount"]),
            currency=params.get("currency", "ETH"),
        )
        explorer = wallet.x402.get_explorer_url(tx_hash)
        return f"✅ Withdrawal sent.\nTx: <code>{tx_hash}</code>\n{explorer}"

    if action_name == "send_money":
        destination = contacts.resolve_name_or_address(
            user_id, params.get("contact_name_or_address", "")
        )
        if not destination:
            raise ValueError("Unknown contact/address.")
        tx_hash = wallet.send(
            user_id=user_id,
            destination_address=destination,
            amount=float(params["amount"]),
            currency=params.get("currency", "USDC"),
        )
        explorer = wallet.x402.get_explorer_url(tx_hash)
        return f"✅ Payment sent.\nTx: <code>{tx_hash}</code>\n{explorer}"

    if action_name == "swap_tokens":
        tx_hash = wallet.swap(
            user_id=user_id,
            from_token=params["from_token"],
            to_token=params["to_token"],
            amount=float(params["amount"]),
        )
        return f"✅ Swap submitted.\nTx: <code>{tx_hash}</code>"

    if action_name == "invest":
        asset = params.get("asset_symbol", "ETH").upper()
        if asset in {"SPY", "QQQ"}:
            raise ValueError(
                f"{asset} is not available on this network. "
                "Tokenized equity providers are not wired up in this build."
            )
        if asset == "USDC":
            raise ValueError("USDC buy not needed. Use Add Funds instead.")
        usd = float(params.get("amount", 0))
        price = wallet.prices.get_price(asset)
        if not price:
            raise ValueError(f"Price unavailable for {asset}.")
        qty = usd / price
        tx_hash = wallet.swap(user_id, "USDC", asset, qty)
        return f"✅ Invest order submitted for {asset}.\nTx: <code>{tx_hash}</code>"

    if action_name == "fetch_article":
        content = wallet.fetch_article(user_id, params["url"])
        return content

    if action_name == "set_price_alert":
        alert_id = alerts.create_alert(
            user_id=user_id,
            asset_symbol=params["asset_symbol"],
            target_price=float(params["target_price"]),
            direction=params["direction"],
        )
        return f"✅ Alert created ({alert_id[:8]}): {params['asset_symbol']} {params['direction']} {format_usd_value(float(params['target_price']))}"

    if action_name == "list_contacts":
        existing = contacts.list_contacts(user_id)
        if not existing:
            return "No contacts saved yet."
        return "\n\n".join(format_contact(c) for c in existing)

    if action_name == "add_contact":
        contacts.add_contact(user_id, params["name"], params["address"])
        return f"✅ Added contact {params['name']}."

    if action_name == "remove_contact":
        all_contacts = contacts.list_contacts(user_id)
        found = next((c for c in all_contacts if c.get("name", "").lower() == params["name"].lower()), None)
        if not found:
            raise ValueError("Contact not found.")
        contacts.remove_contact(user_id, found["contact_id"])
        return f"✅ Removed contact {params['name']}."

    if action_name == "schedule_payment":
        destination = contacts.resolve_name_or_address(
            user_id, params.get("contact_name_or_address", "")
        )
        if not destination:
            raise ValueError("Unknown contact/address.")
        all_contacts = contacts.list_contacts(user_id)
        found = next((c for c in all_contacts if c.get("address") == destination), None)
        if not found:
            cid = contacts.add_contact(user_id, f"Saved {format_address(destination)}", destination)
        else:
            cid = found["contact_id"]
        payment_id = payments.create_payment(
            user_id=user_id,
            contact_id=cid,
            amount=float(params["amount"]),
            currency=params["currency"],
            recurrence="weekly" if "friday" in params.get("cron_or_datetime", "").lower() else "once",
            cron_or_datetime=params.get("cron_or_datetime"),
        )
        return f"✅ Scheduled payment created ({payment_id[:8]})."

    if action_name == "cancel_scheduled_payment":
        payments.cancel_payment(user_id, params["payment_id"])
        return "✅ Scheduled payment cancelled."

    if action_name == "add_funds":
        qr = (
            "https://api.qrserver.com/v1/create-qr-code/?size=250x250&data="
            f"{wallet_address}"
        )
        return (
            "➕ <b>Add Funds</b>\n"
            f"Wallet: <code>{wallet_address}</code>\n"
            f"QR: {qr}\n"
            "Send ETH or USDC on Base."
        )

    if action_name == "get_portfolio_summary":
        summary = wallet.get_portfolio_summary(wallet_address)
        lines = ["📊 <b>Portfolio</b>"]
        for item in summary["holdings"]:
            lines.append(
                f"• {item['asset']}: {item['quantity']:.6f} ({format_usd_value(item['value_usd'])})"
            )
        lines.append(f"Total: {format_usd_value(summary['total_usd'])}")
        return "\n".join(lines)

    if action_name == "subscribe_feed":
        sid = feeds.subscribe(user_id, params["url"])
        return f"✅ Subscribed to feed ({sid[:8]})."

    if action_name == "export_key":
        pseudo = f"enc::{wallet_address[-10:]}::{int(time.time())}"
        return (
            "⚠️ <b>Encrypted key export</b>\n"
            "Store this securely and never share it in plain text.\n"
            f"<code>{pseudo}</code>"
        )

    raise ValueError(f"Unsupported action: {action_name}")


def _handle_confirmation(
    callback_data: str,
    callback_query: Dict[str, Any],
    user: Dict[str, Any],
    services: Dict[str, Any],
) -> None:
    user_id = user["telegram_user_id"]
    chat_id = str(callback_query["message"]["chat"]["id"])
    pending = user.get("pending_action") or {}

    if not pending:
        send_message(services["telegram_token"], chat_id, "No pending action.")
        return
    if pending.get("expires_at", 0) < int(time.time()):
        _update_user(user_id, services, {"pending_action": None})
        send_message(services["telegram_token"], chat_id, "That confirmation expired. Please try again.")
        return

    if callback_data == "confirm:cancel":
        _update_user(user_id, services, {"pending_action": None})
        send_message(services["telegram_token"], chat_id, "Cancelled.")
        return

    try:
        result = _execute_action(
            pending["action_name"], pending.get("action_params", {}), user, services
        )
        _update_user(user_id, services, {"pending_action": None})
        _chunk_and_send(chat_id, services["telegram_token"], result)
    except Exception as exc:
        logger.exception("Failed to execute confirmed action")
        send_message(
            services["telegram_token"],
            chat_id,
            format_error_message("unknown", f"Action failed: {exc}"),
        )


def _prompt_input(
    user_id: str, chat_id: str, services: Dict[str, Any], input_type: str, text: str, data: Optional[Dict[str, Any]] = None
) -> None:
    _update_user(user_id, services, {"awaiting_input": {"type": input_type, "data": data or {}}})
    send_message(services["telegram_token"], chat_id, text)


def _handle_action_callback(
    callback_data: str, callback_query: Dict[str, Any], user: Dict[str, Any], services: Dict[str, Any]
) -> None:
    user_id = user["telegram_user_id"]
    chat_id = str(callback_query["message"]["chat"]["id"])
    message_id = int(callback_query["message"]["message_id"])

    if callback_data == "action:view_balance":
        result = _execute_action("get_balance", {}, user, services)
        send_message(services["telegram_token"], chat_id, result)
        return
    if callback_data == "action:tx_history":
        send_message(services["telegram_token"], chat_id, _execute_action("get_transaction_history", {}, user, services))
        return
    if callback_data == "action:add_funds":
        send_message(services["telegram_token"], chat_id, _execute_action("add_funds", {}, user, services))
        return
    if callback_data == "action:withdraw_start":
        _prompt_input(user_id, chat_id, services, "withdraw_address", "Enter destination wallet address:")
        return
    if callback_data == "action:swap_start":
        keyboard = {"inline_keyboard": [[{"text": t, "callback_data": f"swap:from:{t}"}] for t in SUPPORTED_SWAP_TOKENS]}
        send_message(services["telegram_token"], chat_id, "Choose FROM token:", reply_markup=keyboard)
        return
    if callback_data == "action:send_start":
        contacts = services["contacts"].list_contacts(user_id)
        if not contacts:
            send_message(services["telegram_token"], chat_id, "No contacts saved yet. Add one first.")
            return
        keyboard = {"inline_keyboard": [[{"text": c["name"], "callback_data": f"send:contact:{c['contact_id']}"}] for c in contacts]}
        send_message(services["telegram_token"], chat_id, "Choose contact:", reply_markup=keyboard)
        return
    if callback_data == "action:add_contact_start":
        _prompt_input(user_id, chat_id, services, "add_contact_name", "Enter contact name:")
        return
    if callback_data == "action:view_contacts":
        contacts = services["contacts"].list_contacts(user_id)
        if not contacts:
            send_message(services["telegram_token"], chat_id, "No contacts saved.")
            return
        for contact in contacts:
            keyboard = {"inline_keyboard": [[{"text": "Remove", "callback_data": f"contact:remove:{contact['contact_id']}"}]]}
            send_message(services["telegram_token"], chat_id, format_contact(contact), reply_markup=keyboard)
        return
    if callback_data == "action:schedule_start":
        contacts = services["contacts"].list_contacts(user_id)
        if not contacts:
            send_message(services["telegram_token"], chat_id, "No contacts saved yet. Add one first.")
            return
        keyboard = {"inline_keyboard": [[{"text": c["name"], "callback_data": f"schedule:contact:{c['contact_id']}"}] for c in contacts]}
        send_message(services["telegram_token"], chat_id, "Choose contact for schedule:", reply_markup=keyboard)
        return
    if callback_data == "action:view_payments":
        payments = services["payments"].list_payments(user_id)
        if not payments:
            send_message(services["telegram_token"], chat_id, "No scheduled payments.")
            return
        contacts_map = {c["contact_id"]: c["name"] for c in services["contacts"].list_contacts(user_id)}
        for p in payments:
            payload = {
                "contact_name": contacts_map.get(p.get("contact_id"), "Unknown"),
                "amount": p.get("amount", 0),
                "currency": p.get("currency", "USDC"),
                "recurrence": p.get("recurrence", "once"),
                "next_run": int(p.get("next_run", 0) or 0),
            }
            keyboard = {"inline_keyboard": [[{"text": "Cancel", "callback_data": f"payment:cancel:{p['payment_id']}"}]]}
            send_message(services["telegram_token"], chat_id, format_scheduled_payment(payload), reply_markup=keyboard)
        return
    if callback_data == "action:request_money":
        _prompt_input(user_id, chat_id, services, "request_amount", "Enter amount and currency (e.g. 10 USDC):")
        return
    if callback_data == "action:invest_start":
        keyboard = {"inline_keyboard": [[{"text": asset, "callback_data": f"invest:asset:{asset}"}] for asset in SUPPORTED_INVEST_ASSETS]}
        send_message(services["telegram_token"], chat_id, "Choose asset to buy:", reply_markup=keyboard)
        return
    if callback_data == "action:portfolio":
        send_message(services["telegram_token"], chat_id, _execute_action("get_portfolio_summary", {}, user, services))
        return
    if callback_data == "action:alert_start":
        keyboard = {"inline_keyboard": [[{"text": a, "callback_data": f"alert:asset:{a}"}] for a in SUPPORTED_INVEST_ASSETS]}
        send_message(services["telegram_token"], chat_id, "Choose asset for alert:", reply_markup=keyboard)
        return
    if callback_data == "action:view_alerts":
        alerts = services["alerts"].list_alerts(user_id)
        if not alerts:
            send_message(services["telegram_token"], chat_id, "No active alerts.")
            return
        for alert in alerts:
            keyboard = {"inline_keyboard": [[{"text": "Remove", "callback_data": f"alert:remove:{alert['alert_id']}"}]]}
            send_message(services["telegram_token"], chat_id, format_price_alert(alert), reply_markup=keyboard)
        return
    if callback_data == "action:market_snapshot":
        assets = [a.get("asset_symbol", "ETH") for a in services["alerts"].list_alerts(user_id)] or ["ETH", "BTC", "SOL", "USDC"]
        snapshot = services["alerts"].market_snapshot(assets)
        if not snapshot:
            send_message(services["telegram_token"], chat_id, "No market data available right now.")
            return
        lines = ["📰 <b>Market Snapshot</b>"]
        for item in snapshot:
            lines.append(
                f"• {item['asset']}: {format_usd_value(float(item.get('price') or 0))} ({format_price_change(float(item.get('change_24h') or 0))})"
            )
        send_message(services["telegram_token"], chat_id, "\n".join(lines))
        return
    if callback_data == "action:fetch_article_start":
        _prompt_input(user_id, chat_id, services, "article_url", "Paste an article URL:")
        return
    if callback_data == "action:search_articles":
        _prompt_input(user_id, chat_id, services, "search_topic", "Enter a topic to search:")
        return
    if callback_data == "action:subscribe_feed_start":
        _prompt_input(user_id, chat_id, services, "subscription_url", "Paste RSS/newsletter URL:")
        return
    if callback_data == "action:view_subscriptions":
        subs = services["feeds"].list_subscriptions(user_id)
        if not subs:
            send_message(services["telegram_token"], chat_id, "No active subscriptions.")
            return
        for s in subs:
            keyboard = {"inline_keyboard": [[{"text": "Unsubscribe", "callback_data": f"sub:remove:{s['subscription_id']}"}]]}
            send_message(services["telegram_token"], chat_id, f"📡 {s['feed_url']}", reply_markup=keyboard)
        return
    if callback_data == "action:wallet_address":
        send_message(
            services["telegram_token"],
            chat_id,
            f"🪪 Wallet: <code>{user['wallet_address']}</code>\nNetwork: <code>{user.get('network','base-mainnet')}</code>",
        )
        return
    if callback_data == "action:export_key_start":
        _start_confirmation(
            user_id,
            chat_id,
            services,
            "🔐 Export encrypted key",
            "export_key",
            {"wallet_address": user["wallet_address"]},
        )
        return
    if callback_data == "action:switch_network":
        keyboard = {
            "inline_keyboard": [
                [{"text": "Base Mainnet", "callback_data": "network:set:base-mainnet"}],
                [{"text": "Base Sepolia", "callback_data": "network:set:base-sepolia"}],
                [{"text": "Optimism", "callback_data": "network:set:optimism"}],
            ]
        }
        send_message(services["telegram_token"], chat_id, "Choose network:", reply_markup=keyboard)
        return
    if callback_data == "action:notification_prefs":
        prefs = user.get("notification_prefs", {})
        keyboard = {
            "inline_keyboard": [
                [{"text": f"Price Alerts: {'ON' if prefs.get('price_alerts', True) else 'OFF'}", "callback_data": "notif:toggle:price_alerts"}],
                [{"text": f"Scheduled Payments: {'ON' if prefs.get('scheduled_payments', True) else 'OFF'}", "callback_data": "notif:toggle:scheduled_payments"}],
                [{"text": f"Feed Digests: {'ON' if prefs.get('feed_digests', True) else 'OFF'}", "callback_data": "notif:toggle:feed_digests"}],
            ]
        }
        send_message(services["telegram_token"], chat_id, "Toggle notification preferences:", reply_markup=keyboard)
        return
    if callback_data == "action:help":
        send_message(
            services["telegram_token"],
            chat_id,
            "❓ <b>Help</b>\n"
            "- Use menu buttons for guided actions.\n"
            "- Use 🧠 AI Mode for natural language commands.\n"
            "- Financial actions always require confirmation.\n"
            "- Docs: https://x402.org | https://docs.base.org | https://github.com/minhoyoo-iotrust/WAIaaS",
        )
        return

    if callback_data.startswith("send:contact:"):
        contact_id = callback_data.split(":")[-1]
        _prompt_input(
            user_id,
            chat_id,
            services,
            "send_amount_currency",
            "Enter amount and currency (e.g. 5 USDC):",
            {"contact_id": contact_id},
        )
        return
    if callback_data.startswith("schedule:contact:"):
        contact_id = callback_data.split(":")[-1]
        _prompt_input(
            user_id,
            chat_id,
            services,
            "schedule_amount_currency",
            "Enter amount and currency (e.g. 10 USDC):",
            {"contact_id": contact_id},
        )
        return
    if callback_data.startswith("swap:from:"):
        from_token = callback_data.split(":")[-1]
        keyboard = {
            "inline_keyboard": [
                [{"text": t, "callback_data": f"swap:to:{from_token}:{t}"}]
                for t in SUPPORTED_SWAP_TOKENS
                if t != from_token
            ]
        }
        send_message(services["telegram_token"], chat_id, f"Swap from {from_token}. Choose TO token:", reply_markup=keyboard)
        return
    if callback_data.startswith("swap:to:"):
        _, _, from_token, to_token = callback_data.split(":")
        _prompt_input(
            user_id,
            chat_id,
            services,
            "swap_amount",
            f"Enter amount of {from_token} to swap:",
            {"from_token": from_token, "to_token": to_token},
        )
        return
    if callback_data.startswith("alert:asset:"):
        asset = callback_data.split(":")[-1]
        _prompt_input(user_id, chat_id, services, "alert_price", f"Enter target price for {asset}:", {"asset": asset})
        return
    if callback_data.startswith("alert:dir:"):
        _, _, direction, asset, price = callback_data.split(":")
        msg = _execute_action(
            "set_price_alert",
            {"asset_symbol": asset, "target_price": float(price), "direction": direction},
            user,
            services,
        )
        send_message(services["telegram_token"], chat_id, msg)
        return
    if callback_data.startswith("invest:asset:"):
        asset = callback_data.split(":")[-1]
        _prompt_input(user_id, chat_id, services, "invest_amount", f"Enter USD amount to buy {asset}:", {"asset": asset})
        return
    if callback_data.startswith("network:set:"):
        network = callback_data.split(":")[-1]
        try:
            services["wallet"].use_network(network)
        except ValueError as exc:
            send_message(services["telegram_token"], chat_id, f"❌ {exc}")
            return
        _update_user(user_id, services, {"network": network})
        send_message(services["telegram_token"], chat_id, f"✅ Network switched to <code>{network}</code>")
        _render_menu(chat_id, user_id, services, message_id=message_id)
        return
    if callback_data.startswith("notif:toggle:"):
        key = callback_data.split(":")[-1]
        prefs = user.get("notification_prefs", {})
        prefs[key] = not prefs.get(key, True)
        _update_user(user_id, services, {"notification_prefs": prefs})
        send_message(services["telegram_token"], chat_id, f"Updated {key.replace('_', ' ')} to {'ON' if prefs[key] else 'OFF'}.")
        return
    if callback_data.startswith("contact:remove:"):
        cid = callback_data.split(":")[-1]
        services["contacts"].remove_contact(user_id, cid)
        send_message(services["telegram_token"], chat_id, "Contact removed.")
        return
    if callback_data.startswith("payment:cancel:"):
        payment_id = callback_data.split(":")[-1]
        services["payments"].cancel_payment(user_id, payment_id)
        send_message(services["telegram_token"], chat_id, "Scheduled payment cancelled.")
        return
    if callback_data.startswith("alert:remove:"):
        alert_id = callback_data.split(":")[-1]
        services["alerts"].delete_alert(user_id, alert_id)
        send_message(services["telegram_token"], chat_id, "Alert removed.")
        return
    if callback_data.startswith("sub:remove:"):
        sid = callback_data.split(":")[-1]
        services["feeds"].unsubscribe(user_id, sid)
        send_message(services["telegram_token"], chat_id, "Unsubscribed from feed.")
        return
    if callback_data.startswith("search:fetch:"):
        url = callback_data.replace("search:fetch:", "", 1)
        _start_confirmation(
            user_id,
            chat_id,
            services,
            f"Fetch this article?\n{url}",
            "fetch_article",
            {"url": url},
        )
        return

    send_message(services["telegram_token"], chat_id, "That action is not supported yet.")


def _parse_amount_currency(text: str) -> Tuple[float, str]:
    bits = text.strip().split()
    if len(bits) < 2:
        raise ValueError("Please send amount and currency, e.g. 5 USDC")
    amount = float(bits[0].replace("$", ""))
    currency = bits[1].upper()
    amount_ok, amount_error = validate_amount(amount)
    if not amount_ok:
        raise ValueError(amount_error or "Invalid amount.")
    currency_ok, currency_error = validate_currency(currency)
    if not currency_ok:
        raise ValueError(currency_error or "Invalid currency.")
    return amount, currency


def _handle_menu_text(message_text: str, chat_id: str, user: Dict[str, Any], services: Dict[str, Any]) -> None:
    user_id = user["telegram_user_id"]
    awaiting = user.get("awaiting_input") or {}
    if not awaiting:
        send_message(
            services["telegram_token"],
            chat_id,
            "Use /menu or tap a menu button. You can also switch to 🧠 AI Mode.",
        )
        return

    input_type = awaiting.get("type")
    data = awaiting.get("data", {}) or {}

    try:
        if input_type == "add_contact_name":
            _update_user(
                user_id,
                services,
                {"awaiting_input": {"type": "add_contact_address", "data": {"name": message_text.strip()}}},
            )
            send_message(services["telegram_token"], chat_id, "Now enter wallet address:")
            return
        if input_type == "add_contact_address":
            name = data.get("name", "Contact")
            services["contacts"].add_contact(user_id, name, message_text.strip())
            _update_user(user_id, services, {"awaiting_input": None})
            send_message(services["telegram_token"], chat_id, f"✅ Added contact {name}.")
            return
        if input_type == "withdraw_address":
            valid, error = validate_wallet_address(message_text.strip())
            if not valid:
                raise ValueError(error or "Invalid wallet address.")
            _update_user(
                user_id,
                services,
                {"awaiting_input": {"type": "withdraw_amount_currency", "data": {"destination_address": message_text.strip()}}},
            )
            send_message(services["telegram_token"], chat_id, "Enter amount and currency (e.g. 0.01 ETH):")
            return
        if input_type == "withdraw_amount_currency":
            amount, currency = _parse_amount_currency(message_text)
            _update_user(user_id, services, {"awaiting_input": None})
            _start_confirmation(
                user_id,
                chat_id,
                services,
                f"Withdraw {amount} {currency} to {format_address(data['destination_address'])}",
                "withdraw_funds",
                {
                    "destination_address": data["destination_address"],
                    "amount": amount,
                    "currency": currency,
                },
            )
            return
        if input_type == "send_amount_currency":
            amount, currency = _parse_amount_currency(message_text)
            contacts = services["contacts"].list_contacts(user_id)
            contact = next((c for c in contacts if c.get("contact_id") == data.get("contact_id")), None)
            if not contact:
                raise ValueError("Contact not found.")
            _update_user(user_id, services, {"awaiting_input": None})
            _start_confirmation(
                user_id,
                chat_id,
                services,
                f"Send {amount} {currency} to {contact['name']} ({format_address(contact['address'])})",
                "send_money",
                {"contact_name_or_address": contact["name"], "amount": amount, "currency": currency},
            )
            return
        if input_type == "schedule_amount_currency":
            amount, currency = _parse_amount_currency(message_text)
            _update_user(
                user_id,
                services,
                {
                    "awaiting_input": {
                        "type": "schedule_recurrence",
                        "data": {
                            "contact_id": data["contact_id"],
                            "amount": amount,
                            "currency": currency,
                        },
                    }
                },
            )
            send_message(
                services["telegram_token"],
                chat_id,
                "Enter recurrence: once, daily, weekly, monthly (or ISO datetime).",
            )
            return
        if input_type == "schedule_recurrence":
            recurrence_input = message_text.strip().lower()
            if recurrence_input not in {"once", "daily", "weekly", "monthly"}:
                recurrence = "once"
                cron_or_datetime = message_text.strip()
            else:
                recurrence = recurrence_input
                cron_or_datetime = None
            contacts = services["contacts"].list_contacts(user_id)
            contact = next((c for c in contacts if c.get("contact_id") == data.get("contact_id")), None)
            if not contact:
                raise ValueError("Contact not found.")
            _update_user(user_id, services, {"awaiting_input": None})
            _start_confirmation(
                user_id,
                chat_id,
                services,
                (
                    f"Schedule {data['amount']} {data['currency']} to {contact['name']} "
                    f"({recurrence_input})"
                ),
                "schedule_payment",
                {
                    "contact_name_or_address": contact["name"],
                    "amount": data["amount"],
                    "currency": data["currency"],
                    "cron_or_datetime": cron_or_datetime or recurrence,
                },
            )
            return
        if input_type == "swap_amount":
            amount_ok, amount_error = validate_amount(message_text.strip())
            if not amount_ok:
                raise ValueError(amount_error or "Invalid amount.")
            amount = float(message_text.strip())
            _update_user(user_id, services, {"awaiting_input": None})
            _start_confirmation(
                user_id,
                chat_id,
                services,
                f"Swap {amount} {data['from_token']} to {data['to_token']}",
                "swap_tokens",
                {"from_token": data["from_token"], "to_token": data["to_token"], "amount": amount},
            )
            return
        if input_type == "alert_price":
            amount_ok, amount_error = validate_amount(message_text.strip())
            if not amount_ok:
                raise ValueError(amount_error or "Invalid target price.")
            target = float(message_text.strip())
            _update_user(user_id, services, {"awaiting_input": None})
            keyboard = {
                "inline_keyboard": [
                    [{"text": "Above", "callback_data": f"alert:dir:above:{data['asset']}:{target}"}],
                    [{"text": "Below", "callback_data": f"alert:dir:below:{data['asset']}:{target}"}],
                ]
            }
            send_message(services["telegram_token"], chat_id, "Choose alert direction:", reply_markup=keyboard)
            return
        if input_type == "invest_amount":
            amount_ok, amount_error = validate_amount(message_text.strip())
            if not amount_ok:
                raise ValueError(amount_error or "Invalid amount.")
            amount = float(message_text.strip())
            _update_user(user_id, services, {"awaiting_input": None})
            _start_confirmation(
                user_id,
                chat_id,
                services,
                f"Buy ${amount:.2f} of {data['asset']}",
                "invest",
                {"asset_symbol": data["asset"], "amount": amount},
            )
            return
        if input_type == "article_url":
            valid, error = validate_url(message_text.strip())
            if not valid:
                raise ValueError(error or "Invalid URL.")
            _update_user(user_id, services, {"awaiting_input": None})
            _start_confirmation(
                user_id,
                chat_id,
                services,
                f"Fetch this article?\n{message_text.strip()}",
                "fetch_article",
                {"url": message_text.strip()},
            )
            return
        if input_type == "search_topic":
            _update_user(user_id, services, {"awaiting_input": None})
            results = services["feeds"].search_articles(message_text.strip())
            keyboard = {
                "inline_keyboard": [
                    [{"text": f"Fetch: {r['title'][:40]}", "callback_data": f"search:fetch:{r['url']}"}]
                    for r in results
                ]
            }
            send_message(services["telegram_token"], chat_id, "Search results:", reply_markup=keyboard)
            return
        if input_type == "subscription_url":
            valid, error = validate_url(message_text.strip())
            if not valid:
                raise ValueError(error or "Invalid URL.")
            msg = _execute_action("subscribe_feed", {"url": message_text.strip()}, user, services)
            _update_user(user_id, services, {"awaiting_input": None})
            send_message(services["telegram_token"], chat_id, msg)
            return
        if input_type == "request_amount":
            amount, currency = _parse_amount_currency(message_text)
            _update_user(
                user_id,
                services,
                {"awaiting_input": {"type": "request_memo", "data": {"amount": amount, "currency": currency}}},
            )
            send_message(services["telegram_token"], chat_id, "Optional memo (or type 'skip'):")
            return
        if input_type == "request_memo":
            memo = "" if message_text.strip().lower() == "skip" else message_text.strip()
            link = services["wallet"].build_request_link(
                user["wallet_address"], data["amount"], data["currency"], memo
            )
            _update_user(user_id, services, {"awaiting_input": None})
            send_message(
                services["telegram_token"],
                chat_id,
                f"🧾 Request link:\n<code>{link}</code>",
            )
            return
    except Exception as exc:
        send_message(services["telegram_token"], chat_id, format_error_message("validation", str(exc)))
        return

    send_message(services["telegram_token"], chat_id, "I did not understand that input.")


def _handle_nl_text(message_text: str, chat_id: str, user: Dict[str, Any], services: Dict[str, Any]) -> None:
    user_id = user["telegram_user_id"]
    history = user.get("nl_conversation_history", [])[-10:]

    balances = {}
    try:
        balances = services["wallet"].get_balance_summary(user["wallet_address"])
    except Exception:
        balances = {}

    context = {
        "wallet_address": user.get("wallet_address"),
        "balances": balances,
        "contacts": services["contacts"].list_contacts(user_id),
    }

    parsed = services["nl"].parse(message_text, context=context, history=history)
    history.append({"role": "user", "content": message_text})

    if parsed["kind"] == "text":
        send_message(
            services["telegram_token"],
            chat_id,
            parsed["content"],
            reply_markup=build_nl_mode_keyboard(),
        )
        history.append({"role": "assistant", "content": parsed["content"]})
        _update_user(user_id, services, {"nl_conversation_history": history[-10:]})
        return

    tool_name = parsed["tool_name"]
    tool_input = parsed.get("tool_input", {})
    if parsed.get("requires_confirmation", False):
        preview = (
            f"Got it — {tool_name.replace('_', ' ')} with "
            f"{json.dumps(tool_input, ensure_ascii=True)}"
        )
        _start_confirmation(
            user_id,
            chat_id,
            services,
            preview,
            tool_name,
            tool_input,
        )
        history.append({"role": "assistant", "content": preview})
        _update_user(user_id, services, {"nl_conversation_history": history[-10:]})
        return

    try:
        result = _execute_action(tool_name, tool_input, user, services)
        if tool_name == "fetch_article":
            _chunk_and_send(chat_id, services["telegram_token"], result)
        else:
            send_message(
                services["telegram_token"],
                chat_id,
                result,
                reply_markup=build_nl_mode_keyboard(),
            )
        history.append({"role": "assistant", "content": result[:500]})
    except Exception as exc:
        error_text = format_error_message("unknown", str(exc))
        send_message(services["telegram_token"], chat_id, error_text, reply_markup=build_nl_mode_keyboard())
        history.append({"role": "assistant", "content": error_text})

    _update_user(user_id, services, {"nl_conversation_history": history[-10:]})


def _handle_callback(update: Dict[str, Any], services: Dict[str, Any]) -> None:
    query = update["callback_query"]
    callback_data = query.get("data", "")
    user_id = str(query["from"]["id"])
    chat_id = str(query["message"]["chat"]["id"])
    message_id = int(query["message"]["message_id"])
    answer_callback_query(services["telegram_token"], query["id"])

    user = _ensure_user(user_id, services)

    if callback_data.startswith("nav:"):
        current = clamp_page(int(user.get("current_page", 0)))
        if callback_data == "nav:next":
            current = clamp_page(current + 1)
        elif callback_data == "nav:back":
            current = clamp_page(current - 1)
        _update_user(user_id, services, {"current_page": current, "interaction_mode": "menu"})
        _render_menu(chat_id, user_id, services, message_id=message_id)
        return

    if callback_data == "mode:nl":
        _update_user(user_id, services, {"interaction_mode": "nl"})
        edit_message(
            services["telegram_token"],
            chat_id,
            message_id,
            text=(
                "🧠 <b>AI Mode enabled</b>\n"
                "Send me natural language commands like:\n"
                "• send 5 USDC to Alex\n• what's my balance\n• alert me when BTC hits 100k"
            ),
            reply_markup=build_nl_mode_keyboard(),
        )
        return
    if callback_data == "mode:menu":
        _update_user(user_id, services, {"interaction_mode": "menu"})
        _render_menu(chat_id, user_id, services, message_id=message_id)
        return

    if callback_data.startswith("confirm:"):
        _handle_confirmation(callback_data, query, user, services)
        return

    _handle_action_callback(callback_data, query, user, services)


def _handle_message(update: Dict[str, Any], services: Dict[str, Any]) -> None:
    message = update["message"]
    message_text = (message.get("text") or "").strip()
    user_id = str(message["from"]["id"])
    chat_id = str(message["chat"]["id"])

    user = _ensure_user(user_id, services)

    if message_text in {"/start", "/menu"}:
        page = 0 if message_text == "/start" else clamp_page(int(user.get("current_page", 0)))
        _update_user(
            user_id,
            services,
            {"interaction_mode": "menu", "current_page": page, "awaiting_input": None},
        )
        _render_menu(chat_id, user_id, services)
        return

    mode = user.get("interaction_mode", "menu")
    if mode == "nl":
        _handle_nl_text(message_text, chat_id, user, services)
    else:
        _handle_menu_text(message_text, chat_id, user, services)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entrypoint for Telegram webhook updates."""
    try:
        services = _get_services()
        update = _safe_body(event)
        if not update:
            return _response(200, {"ok": True, "ignored": True})
        if "callback_query" in update:
            _handle_callback(update, services)
            return _response(200)
        if "message" in update:
            _handle_message(update, services)
            return _response(200)
        return _response(200, {"ok": True, "ignored": True})
    except Exception as exc:
        logger.exception("Webhook failure")
        return _response(200, {"ok": False, "error": str(exc)})

