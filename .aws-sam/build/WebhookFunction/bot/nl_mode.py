"""Claude-powered natural language mode with tool mapping."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

try:
    from anthropic import Anthropic
except Exception:  # pragma: no cover - keeps local tests resilient
    Anthropic = None  # type: ignore


CLAUDE_MODEL = "claude-sonnet-4-20250514"

FINANCIAL_TOOLS = {
    "withdraw_funds",
    "send_money",
    "invest",
    "schedule_payment",
    "swap_tokens",
}

CLAUDE_TOOLS: List[Dict[str, Any]] = [
    {"name": "get_balance", "description": "Get wallet balances.", "input_schema": {"type": "object", "properties": {}}},
    {
        "name": "get_transaction_history",
        "description": "Get transaction history.",
        "input_schema": {"type": "object", "properties": {"limit": {"type": "integer"}}, "required": []},
    },
    {"name": "add_funds", "description": "Get deposit details.", "input_schema": {"type": "object", "properties": {"amount": {"type": "number"}}, "required": []}},
    {
        "name": "withdraw_funds",
        "description": "Withdraw funds to external wallet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destination_address": {"type": "string"},
                "amount": {"type": "number"},
                "currency": {"type": "string"},
            },
            "required": ["destination_address", "amount"],
        },
    },
    {
        "name": "send_money",
        "description": "Send money to contact or address.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_name_or_address": {"type": "string"},
                "amount": {"type": "number"},
                "currency": {"type": "string"},
            },
            "required": ["contact_name_or_address", "amount", "currency"],
        },
    },
    {
        "name": "invest",
        "description": "Buy an asset using USD amount.",
        "input_schema": {"type": "object", "properties": {"asset_symbol": {"type": "string"}, "amount": {"type": "number"}}, "required": ["asset_symbol", "amount"]},
    },
    {"name": "fetch_article", "description": "Fetch article by URL.", "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
    {
        "name": "set_price_alert",
        "description": "Set a price alert.",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_symbol": {"type": "string"},
                "target_price": {"type": "number"},
                "direction": {"type": "string", "enum": ["above", "below"]},
            },
            "required": ["asset_symbol", "target_price", "direction"],
        },
    },
    {"name": "list_contacts", "description": "List contacts.", "input_schema": {"type": "object", "properties": {}}},
    {
        "name": "add_contact",
        "description": "Add contact.",
        "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "address": {"type": "string"}}, "required": ["name", "address"]},
    },
    {"name": "remove_contact", "description": "Remove contact by name.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {
        "name": "schedule_payment",
        "description": "Schedule payment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_name_or_address": {"type": "string"},
                "amount": {"type": "number"},
                "currency": {"type": "string"},
                "cron_or_datetime": {"type": "string"},
            },
            "required": ["contact_name_or_address", "amount", "currency", "cron_or_datetime"],
        },
    },
    {"name": "cancel_scheduled_payment", "description": "Cancel scheduled payment.", "input_schema": {"type": "object", "properties": {"payment_id": {"type": "string"}}, "required": ["payment_id"]}},
    {
        "name": "swap_tokens",
        "description": "Swap two tokens.",
        "input_schema": {"type": "object", "properties": {"from_token": {"type": "string"}, "to_token": {"type": "string"}, "amount": {"type": "number"}}, "required": ["from_token", "to_token", "amount"]},
    },
    {"name": "get_portfolio_summary", "description": "Get holdings summary.", "input_schema": {"type": "object", "properties": {}}},
]


class NLModeService:
    """Runs Claude tool selection and normalizes a result."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = Anthropic(api_key=api_key) if api_key and Anthropic else None

    @staticmethod
    def _build_system_prompt(context: Dict[str, Any]) -> str:
        return (
            "You are a Telegram personal finance agent. "
            "Always prefer tool_use to map user intent to one defined tool. "
            "If unclear, ask a short clarifying question.\n\n"
            f"Wallet address: {context.get('wallet_address', 'unknown')}\n"
            f"Balances: {json.dumps(context.get('balances', {}))}\n"
            f"Contacts: {json.dumps(context.get('contacts', []))}\n"
            "Before financial actions, the app will ask for confirmation."
        )

    def parse(
        self, message: str, context: Dict[str, Any], history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        history = history or []
        if self.client:
            result = self._parse_with_claude(message, context, history)
            if result:
                return result
        return self._parse_with_heuristics(message)

    def _parse_with_claude(
        self, message: str, context: Dict[str, Any], history: List[Dict[str, str]]
    ) -> Optional[Dict[str, Any]]:
        try:
            messages = []
            for turn in history[-10:]:
                messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})
            messages.append({"role": "user", "content": message})

            response = self.client.messages.create(  # type: ignore[union-attr]
                model=CLAUDE_MODEL,
                max_tokens=500,
                system=self._build_system_prompt(context),
                tools=CLAUDE_TOOLS,
                messages=messages,
            )

            text_chunks: List[str] = []
            for block in response.content:
                block_type = getattr(block, "type", None)
                if block_type == "tool_use":
                    tool_name = getattr(block, "name", "")
                    tool_input = getattr(block, "input", {}) or {}
                    return {
                        "kind": "tool",
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "requires_confirmation": tool_name in FINANCIAL_TOOLS,
                    }
                if block_type == "text":
                    text_chunks.append(getattr(block, "text", ""))
            if text_chunks:
                return {"kind": "text", "content": "\n".join(text_chunks).strip()}
        except Exception:
            return None
        return None

    @staticmethod
    def _parse_with_heuristics(message: str) -> Dict[str, Any]:
        lower = message.lower().strip()
        if "balance" in lower:
            return {"kind": "tool", "tool_name": "get_balance", "tool_input": {}, "requires_confirmation": False}
        if "last" in lower and "transaction" in lower:
            match = re.search(r"(\d+)", lower)
            return {
                "kind": "tool",
                "tool_name": "get_transaction_history",
                "tool_input": {"limit": int(match.group(1)) if match else 10},
                "requires_confirmation": False,
            }
        if lower.startswith("send ") or " send " in lower:
            amount_match = re.search(r"(\d+(\.\d+)?)", lower)
            currency = "USDC" if "usdc" in lower else "ETH"
            target = lower.split(" to ")[-1].strip() if " to " in lower else ""
            return {
                "kind": "tool",
                "tool_name": "send_money",
                "tool_input": {
                    "contact_name_or_address": target,
                    "amount": float(amount_match.group(1)) if amount_match else 0.0,
                    "currency": currency,
                },
                "requires_confirmation": True,
            }
        if "alert" in lower and ("btc" in lower or "eth" in lower or "sol" in lower):
            asset = "BTC" if "btc" in lower else "ETH" if "eth" in lower else "SOL"
            amount_match = re.search(r"(\d+(\.\d+)?)(k)?", lower)
            target = 0.0
            if amount_match:
                target = float(amount_match.group(1))
                if amount_match.group(3):
                    target *= 1000
            direction = "below" if "below" in lower else "above"
            return {
                "kind": "tool",
                "tool_name": "set_price_alert",
                "tool_input": {"asset_symbol": asset, "target_price": target, "direction": direction},
                "requires_confirmation": False,
            }
        return {
            "kind": "text",
            "content": (
                "I can help with balance, transfers, alerts, swaps, schedules, and article fetches. "
                "Try something like: 'send 5 USDC to Alex'."
            ),
        }

