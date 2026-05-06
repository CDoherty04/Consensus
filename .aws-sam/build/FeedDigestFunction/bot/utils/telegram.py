"""
Telegram API helper functions for the Telegram AI Finance Bot.

This module provides utility functions for interacting with the Telegram Bot API,
including sending messages, editing messages, sending inline keyboards, and
answering callback queries.
"""

import requests
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TelegramAPIError(Exception):
    """Exception raised when Telegram API calls fail."""
    pass


def send_message(
    bot_token: str,
    chat_id: str,
    text: str,
    reply_markup: Optional[Dict[str, Any]] = None,
    parse_mode: str = "HTML"
) -> Dict[str, Any]:
    """
    Send a text message to a Telegram chat.
    
    Args:
        bot_token: Telegram bot authentication token
        chat_id: Unique identifier for the target chat
        text: Text of the message to be sent
        reply_markup: Optional inline keyboard markup
        parse_mode: Mode for parsing entities in the message text (default: HTML)
        
    Returns:
        dict: Response from Telegram API containing message details
        
    Raises:
        TelegramAPIError: If the API request fails
        
    Example:
        >>> send_message(
        ...     bot_token="123:ABC",
        ...     chat_id="456",
        ...     text="Hello, world!"
        ... )
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if not result.get("ok"):
            error_msg = result.get("description", "Unknown error")
            logger.error(f"Telegram API error: {error_msg}")
            raise TelegramAPIError(f"Failed to send message: {error_msg}")
        
        return result.get("result", {})
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        raise TelegramAPIError(f"Failed to send message: {str(e)}")


def edit_message(
    bot_token: str,
    chat_id: str,
    message_id: int,
    text: Optional[str] = None,
    reply_markup: Optional[Dict[str, Any]] = None,
    parse_mode: str = "HTML"
) -> Dict[str, Any]:
    """
    Edit an existing message in-place for page transitions.
    
    This function supports editing either the text, the reply markup (inline keyboard),
    or both. At least one of text or reply_markup must be provided.
    
    Args:
        bot_token: Telegram bot authentication token
        chat_id: Unique identifier for the target chat
        message_id: Identifier of the message to edit
        text: Optional new text of the message
        reply_markup: Optional new inline keyboard markup
        parse_mode: Mode for parsing entities in the message text (default: HTML)
        
    Returns:
        dict: Response from Telegram API containing updated message details
        
    Raises:
        TelegramAPIError: If the API request fails
        ValueError: If neither text nor reply_markup is provided
        
    Example:
        >>> edit_message(
        ...     bot_token="123:ABC",
        ...     chat_id="456",
        ...     message_id=789,
        ...     text="Updated text",
        ...     reply_markup={"inline_keyboard": [[{"text": "Button", "callback_data": "action"}]]}
        ... )
    """
    if text is None and reply_markup is None:
        raise ValueError("At least one of text or reply_markup must be provided")
    
    # Use editMessageText if text is provided, otherwise editMessageReplyMarkup
    if text is not None:
        url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
    else:
        url = f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "reply_markup": reply_markup
        }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if not result.get("ok"):
            error_msg = result.get("description", "Unknown error")
            logger.error(f"Telegram API error: {error_msg}")
            raise TelegramAPIError(f"Failed to edit message: {error_msg}")
        
        return result.get("result", {})
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        raise TelegramAPIError(f"Failed to edit message: {str(e)}")


def send_inline_keyboard(
    bot_token: str,
    chat_id: str,
    text: str,
    buttons: List[List[Dict[str, str]]],
    parse_mode: str = "HTML"
) -> Dict[str, Any]:
    """
    Send a message with an inline keyboard.
    
    Args:
        bot_token: Telegram bot authentication token
        chat_id: Unique identifier for the target chat
        text: Text of the message to be sent
        buttons: 2D array of button objects, where each inner array represents a row
                 Each button should have 'text' and 'callback_data' keys
        parse_mode: Mode for parsing entities in the message text (default: HTML)
        
    Returns:
        dict: Response from Telegram API containing message details
        
    Raises:
        TelegramAPIError: If the API request fails
        
    Example:
        >>> send_inline_keyboard(
        ...     bot_token="123:ABC",
        ...     chat_id="456",
        ...     text="Choose an option:",
        ...     buttons=[
        ...         [{"text": "Option 1", "callback_data": "opt1"}],
        ...         [{"text": "Option 2", "callback_data": "opt2"}]
        ...     ]
        ... )
    """
    reply_markup = {
        "inline_keyboard": buttons
    }
    
    return send_message(
        bot_token=bot_token,
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode
    )


def answer_callback_query(
    bot_token: str,
    callback_query_id: str,
    text: Optional[str] = None,
    show_alert: bool = False
) -> Dict[str, Any]:
    """
    Answer a callback query from an inline keyboard button.
    
    This function should be called after processing a callback query to remove
    the loading state from the button and optionally show a notification to the user.
    
    Args:
        bot_token: Telegram bot authentication token
        callback_query_id: Unique identifier for the query to be answered
        text: Optional text of the notification (0-200 characters)
        show_alert: If True, an alert will be shown instead of a notification
                   at the top of the chat screen
        
    Returns:
        dict: Response from Telegram API
        
    Raises:
        TelegramAPIError: If the API request fails
        
    Example:
        >>> answer_callback_query(
        ...     bot_token="123:ABC",
        ...     callback_query_id="query123",
        ...     text="Action completed!",
        ...     show_alert=False
        ... )
    """
    url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
    
    payload = {
        "callback_query_id": callback_query_id,
        "show_alert": show_alert
    }
    
    if text:
        payload["text"] = text[:200]  # Telegram limit is 200 characters
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if not result.get("ok"):
            error_msg = result.get("description", "Unknown error")
            logger.error(f"Telegram API error: {error_msg}")
            raise TelegramAPIError(f"Failed to answer callback query: {error_msg}")
        
        return result.get("result", {})
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        raise TelegramAPIError(f"Failed to answer callback query: {str(e)}")
