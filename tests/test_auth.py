from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, Message, Update, User

from bot.auth import authorized_only, is_authorized
from config.settings import Settings


@pytest.fixture
def test_settings():
    return Settings(
        telegram_bot_token="test_token",
        telegram_allowed_user_id=12345,
        telegram_allowed_chat_id=67890,
    )


def test_is_authorized(test_settings):
    # Authorized case
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User, id=12345)
    update.effective_chat = MagicMock(spec=Chat, id=67890)
    assert is_authorized(update, test_settings) is True

    # Wrong user ID
    update.effective_user.id = 99999
    assert is_authorized(update, test_settings) is False

    # Wrong chat ID
    update.effective_user.id = 12345
    update.effective_chat.id = 99999
    assert is_authorized(update, test_settings) is False

    # None user
    update.effective_user = None
    assert is_authorized(update, test_settings) is False


@pytest.mark.asyncio
async def test_authorized_only_decorator(test_settings):
    mock_handler = AsyncMock(return_value="executed")
    decorated = authorized_only(mock_handler)

    context = MagicMock()
    context.bot_data = {"settings": test_settings}

    # Authorized call
    auth_update = MagicMock(spec=Update)
    auth_update.effective_user = MagicMock(spec=User, id=12345)
    auth_update.effective_chat = MagicMock(spec=Chat, id=67890)
    auth_update.effective_message = MagicMock(spec=Message)

    result = await decorated(auth_update, context)
    assert result == "executed"
    assert mock_handler.call_count == 1

    # Unauthorized call
    unauth_update = MagicMock(spec=Update)
    unauth_update.effective_user = MagicMock(spec=User, id=99999)
    unauth_update.effective_chat = MagicMock(spec=Chat, id=99999)
    unauth_update.effective_message = MagicMock(spec=Message)
    unauth_update.effective_message.reply_text = AsyncMock()

    unauth_result = await decorated(unauth_update, context)
    assert unauth_result is None
    assert mock_handler.call_count == 1  # Not incremented
    unauth_update.effective_message.reply_text.assert_called_once_with(
        "⛔ Unauthorized access."
    )
