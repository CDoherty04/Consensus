"""Menu page rendering for the Telegram finance bot."""

from typing import Any, Dict, List, Tuple

TOTAL_PAGES = 5

PAGE_TITLES = {
    0: "💼 Agent Finances",
    1: "💸 Send & Pay",
    2: "📈 Invest & Trade",
    3: "📰 Content & Data",
    4: "⚙️ Settings & Account",
}

PAGE_ACTIONS: Dict[int, List[Tuple[str, str]]] = {
    0: [
        ("💰 View Balance", "action:view_balance"),
        ("📋 Transaction History", "action:tx_history"),
        ("➕ Add Funds", "action:add_funds"),
        ("➖ Withdraw Funds", "action:withdraw_start"),
        ("🔄 Swap Tokens", "action:swap_start"),
    ],
    1: [
        ("📤 Send Money", "action:send_start"),
        ("⏰ Schedule Payment", "action:schedule_start"),
        ("📅 Upcoming Payments", "action:view_payments"),
        ("🧾 Request Money", "action:request_money"),
        ("➕ Add Contact", "action:add_contact_start"),
        ("👥 View Contacts", "action:view_contacts"),
    ],
    2: [
        ("🛒 Buy Asset", "action:invest_start"),
        ("📊 Portfolio Summary", "action:portfolio"),
        ("🔔 Set Price Alert", "action:alert_start"),
        ("📉 View Alerts", "action:view_alerts"),
        ("📰 Market Snapshot", "action:market_snapshot"),
    ],
    3: [
        ("🔓 Fetch Article", "action:fetch_article_start"),
        ("🔍 Search Articles", "action:search_articles"),
        ("📡 Subscribe to Feed", "action:subscribe_feed_start"),
        ("📋 My Subscriptions", "action:view_subscriptions"),
    ],
    4: [
        ("🪪 My Wallet Address", "action:wallet_address"),
        ("🔐 Export Private Key", "action:export_key_start"),
        ("🌐 Switch Network", "action:switch_network"),
        ("🔔 Notification Prefs", "action:notification_prefs"),
        ("🧠 AI Mode", "mode:nl"),
        ("❓ Help", "action:help"),
    ],
}


def clamp_page(page: int) -> int:
    """Clamp page index to valid bounds."""
    return max(0, min(page, TOTAL_PAGES - 1))


def build_menu_page(page: int, network: str = "base-mainnet") -> Dict[str, Any]:
    """Build page text and keyboard payload."""
    page = clamp_page(page)
    title = PAGE_TITLES[page]

    text_lines = [
        f"<b>{title}</b>",
        "",
        f"Network: <code>{network}</code>",
        "Choose an action:",
    ]

    keyboard: List[List[Dict[str, str]]] = []
    for label, callback_data in PAGE_ACTIONS[page]:
        keyboard.append([{"text": label, "callback_data": callback_data}])

    keyboard.append(
        [
            {"text": "← Back", "callback_data": "nav:back"},
            {"text": f"Page {page + 1}/{TOTAL_PAGES}", "callback_data": "nav:noop"},
            {"text": "Next →", "callback_data": "nav:next"},
        ]
    )
    if page != 4:
        keyboard.append([{"text": "🧠 AI Mode", "callback_data": "mode:nl"}])

    return {"text": "\n".join(text_lines), "reply_markup": {"inline_keyboard": keyboard}}


def build_nl_mode_keyboard() -> Dict[str, Any]:
    """Return keyboard shown while user is in NL mode."""
    return {
        "inline_keyboard": [[{"text": "📋 Menu Mode", "callback_data": "mode:menu"}]]
    }

