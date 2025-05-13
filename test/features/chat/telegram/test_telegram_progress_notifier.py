import unittest
from unittest.mock import Mock, patch

from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.telegram.telegram_progress_notifier import TelegramProgressNotifier, ChatConfig


class TelegramProgressNotifierTest(unittest.TestCase):
    chat_config: ChatConfig
    message_id: str
    mock_bot_sdk: Mock
    notifier: TelegramProgressNotifier

    def setUp(self):
        self.chat_config = ChatConfig(
            chat_id = "test_chat_id",
            language_iso_code = "en",
            language_name = "English",
            title = "Test Chat",
            is_private = True,
            reply_chance_percent = 100
        )
        self.message_id = "test_message_id"
        self.mock_bot_sdk = Mock(spec = TelegramBotSDK)
        self.mock_bot_sdk.api = Mock(spec = TelegramBotAPI)
        self.notifier = TelegramProgressNotifier(
            chat_config = self.chat_config,
            message_id = self.message_id,
            bot_sdk = self.mock_bot_sdk,
            auto_start = False
        )

    # noinspection PyUnresolvedReferences
    def test_init(self):
        self.assertEqual(self.notifier._TelegramProgressNotifier__chat_config, self.chat_config)
        self.assertEqual(self.notifier._TelegramProgressNotifier__message_id, self.message_id)

    @patch("features.chat.telegram.telegram_progress_notifier.Thread")
    def test_start(self, mock_thread):
        self.notifier.start()
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

    @patch("features.chat.telegram.telegram_progress_notifier.Thread")
    def test_stop(self, mock_thread):
        self.notifier.start()
        self.notifier.stop()
        mock_thread.return_value.join.assert_called_once_with(timeout = 1)

    @patch("features.chat.telegram.telegram_progress_notifier.time.time")
    def test_send_reaction(self, mock_time):
        mock_time.return_value = 100
        # noinspection PyUnresolvedReferences
        self.notifier._TelegramProgressNotifier__send_reaction()
        self.mock_bot_sdk.set_status_typing.assert_called_once_with(self.chat_config.chat_id)
        self.mock_bot_sdk.set_reaction.assert_called_once()
