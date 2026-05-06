"""
Unit tests for Telegram API helper functions.
"""

import pytest
from unittest.mock import Mock, patch
import requests
from bot.utils.telegram import (
    send_message,
    edit_message,
    send_inline_keyboard,
    answer_callback_query,
    TelegramAPIError
)


class TestSendMessage:
    """Tests for send_message function."""
    
    @patch('bot.utils.telegram.requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful message sending."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {
                "message_id": 123,
                "text": "Hello, world!"
            }
        }
        mock_post.return_value = mock_response
        
        result = send_message(
            bot_token="test_token",
            chat_id="456",
            text="Hello, world!"
        )
        
        assert result["message_id"] == 123
        assert result["text"] == "Hello, world!"
        mock_post.assert_called_once()
        
        # Verify the request payload
        call_args = mock_post.call_args
        assert call_args[1]["json"]["chat_id"] == "456"
        assert call_args[1]["json"]["text"] == "Hello, world!"
        assert call_args[1]["json"]["parse_mode"] == "HTML"
    
    @patch('bot.utils.telegram.requests.post')
    def test_send_message_with_reply_markup(self, mock_post):
        """Test sending message with inline keyboard."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 123}
        }
        mock_post.return_value = mock_response
        
        reply_markup = {
            "inline_keyboard": [[{"text": "Button", "callback_data": "action"}]]
        }
        
        result = send_message(
            bot_token="test_token",
            chat_id="456",
            text="Choose:",
            reply_markup=reply_markup
        )
        
        assert result["message_id"] == 123
        
        # Verify reply_markup was included
        call_args = mock_post.call_args
        assert call_args[1]["json"]["reply_markup"] == reply_markup
    
    @patch('bot.utils.telegram.requests.post')
    def test_send_message_api_error(self, mock_post):
        """Test handling of Telegram API error response."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": False,
            "description": "Bad Request: chat not found"
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(TelegramAPIError) as exc_info:
            send_message(
                bot_token="test_token",
                chat_id="invalid",
                text="Test"
            )
        
        assert "chat not found" in str(exc_info.value)
    
    @patch('bot.utils.telegram.requests.post')
    def test_send_message_network_error(self, mock_post):
        """Test handling of network errors."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")
        
        with pytest.raises(TelegramAPIError) as exc_info:
            send_message(
                bot_token="test_token",
                chat_id="456",
                text="Test"
            )
        
        assert "Network error" in str(exc_info.value)


class TestEditMessage:
    """Tests for edit_message function."""
    
    @patch('bot.utils.telegram.requests.post')
    def test_edit_message_text_only(self, mock_post):
        """Test editing message text only."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {
                "message_id": 123,
                "text": "Updated text"
            }
        }
        mock_post.return_value = mock_response
        
        result = edit_message(
            bot_token="test_token",
            chat_id="456",
            message_id=123,
            text="Updated text"
        )
        
        assert result["text"] == "Updated text"
        
        # Verify editMessageText endpoint was used
        call_args = mock_post.call_args
        assert "editMessageText" in call_args[0][0]
        assert call_args[1]["json"]["text"] == "Updated text"
    
    @patch('bot.utils.telegram.requests.post')
    def test_edit_message_reply_markup_only(self, mock_post):
        """Test editing reply markup only."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 123}
        }
        mock_post.return_value = mock_response
        
        reply_markup = {
            "inline_keyboard": [[{"text": "New Button", "callback_data": "new"}]]
        }
        
        result = edit_message(
            bot_token="test_token",
            chat_id="456",
            message_id=123,
            reply_markup=reply_markup
        )
        
        assert result["message_id"] == 123
        
        # Verify editMessageReplyMarkup endpoint was used
        call_args = mock_post.call_args
        assert "editMessageReplyMarkup" in call_args[0][0]
        assert call_args[1]["json"]["reply_markup"] == reply_markup
    
    @patch('bot.utils.telegram.requests.post')
    def test_edit_message_text_and_markup(self, mock_post):
        """Test editing both text and reply markup."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 123}
        }
        mock_post.return_value = mock_response
        
        reply_markup = {
            "inline_keyboard": [[{"text": "Button", "callback_data": "action"}]]
        }
        
        result = edit_message(
            bot_token="test_token",
            chat_id="456",
            message_id=123,
            text="New text",
            reply_markup=reply_markup
        )
        
        # Verify editMessageText endpoint was used (takes precedence)
        call_args = mock_post.call_args
        assert "editMessageText" in call_args[0][0]
        assert call_args[1]["json"]["text"] == "New text"
        assert call_args[1]["json"]["reply_markup"] == reply_markup
    
    def test_edit_message_no_parameters(self):
        """Test that ValueError is raised when neither text nor reply_markup is provided."""
        with pytest.raises(ValueError) as exc_info:
            edit_message(
                bot_token="test_token",
                chat_id="456",
                message_id=123
            )
        
        assert "At least one of text or reply_markup must be provided" in str(exc_info.value)
    
    @patch('bot.utils.telegram.requests.post')
    def test_edit_message_api_error(self, mock_post):
        """Test handling of API error when editing message."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": False,
            "description": "Bad Request: message not found"
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(TelegramAPIError) as exc_info:
            edit_message(
                bot_token="test_token",
                chat_id="456",
                message_id=999,
                text="Test"
            )
        
        assert "message not found" in str(exc_info.value)


class TestSendInlineKeyboard:
    """Tests for send_inline_keyboard function."""
    
    @patch('bot.utils.telegram.requests.post')
    def test_send_inline_keyboard_success(self, mock_post):
        """Test sending message with inline keyboard."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 123}
        }
        mock_post.return_value = mock_response
        
        buttons = [
            [{"text": "Option 1", "callback_data": "opt1"}],
            [{"text": "Option 2", "callback_data": "opt2"}]
        ]
        
        result = send_inline_keyboard(
            bot_token="test_token",
            chat_id="456",
            text="Choose an option:",
            buttons=buttons
        )
        
        assert result["message_id"] == 123
        
        # Verify the inline keyboard was properly formatted
        call_args = mock_post.call_args
        assert call_args[1]["json"]["reply_markup"]["inline_keyboard"] == buttons
    
    @patch('bot.utils.telegram.requests.post')
    def test_send_inline_keyboard_multiple_rows(self, mock_post):
        """Test sending inline keyboard with multiple buttons per row."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 123}
        }
        mock_post.return_value = mock_response
        
        buttons = [
            [
                {"text": "Button 1", "callback_data": "btn1"},
                {"text": "Button 2", "callback_data": "btn2"}
            ],
            [{"text": "Button 3", "callback_data": "btn3"}]
        ]
        
        result = send_inline_keyboard(
            bot_token="test_token",
            chat_id="456",
            text="Multiple buttons:",
            buttons=buttons
        )
        
        assert result["message_id"] == 123


class TestAnswerCallbackQuery:
    """Tests for answer_callback_query function."""
    
    @patch('bot.utils.telegram.requests.post')
    def test_answer_callback_query_no_text(self, mock_post):
        """Test answering callback query without notification text."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": True
        }
        mock_post.return_value = mock_response
        
        result = answer_callback_query(
            bot_token="test_token",
            callback_query_id="query123"
        )
        
        assert result is True
        
        # Verify the request
        call_args = mock_post.call_args
        assert call_args[1]["json"]["callback_query_id"] == "query123"
        assert call_args[1]["json"]["show_alert"] is False
        assert "text" not in call_args[1]["json"]
    
    @patch('bot.utils.telegram.requests.post')
    def test_answer_callback_query_with_text(self, mock_post):
        """Test answering callback query with notification text."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": True
        }
        mock_post.return_value = mock_response
        
        result = answer_callback_query(
            bot_token="test_token",
            callback_query_id="query123",
            text="Action completed!"
        )
        
        assert result is True
        
        # Verify the text was included
        call_args = mock_post.call_args
        assert call_args[1]["json"]["text"] == "Action completed!"
    
    @patch('bot.utils.telegram.requests.post')
    def test_answer_callback_query_with_alert(self, mock_post):
        """Test answering callback query with alert."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": True
        }
        mock_post.return_value = mock_response
        
        result = answer_callback_query(
            bot_token="test_token",
            callback_query_id="query123",
            text="Important alert!",
            show_alert=True
        )
        
        assert result is True
        
        # Verify show_alert was set
        call_args = mock_post.call_args
        assert call_args[1]["json"]["show_alert"] is True
    
    @patch('bot.utils.telegram.requests.post')
    def test_answer_callback_query_text_truncation(self, mock_post):
        """Test that text is truncated to 200 characters."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": True
        }
        mock_post.return_value = mock_response
        
        long_text = "a" * 300  # 300 characters
        
        result = answer_callback_query(
            bot_token="test_token",
            callback_query_id="query123",
            text=long_text
        )
        
        # Verify text was truncated to 200 characters
        call_args = mock_post.call_args
        assert len(call_args[1]["json"]["text"]) == 200
    
    @patch('bot.utils.telegram.requests.post')
    def test_answer_callback_query_api_error(self, mock_post):
        """Test handling of API error when answering callback query."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": False,
            "description": "Bad Request: query is too old"
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(TelegramAPIError) as exc_info:
            answer_callback_query(
                bot_token="test_token",
                callback_query_id="old_query"
            )
        
        assert "query is too old" in str(exc_info.value)
