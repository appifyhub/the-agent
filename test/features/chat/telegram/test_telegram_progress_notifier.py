import unittest
from unittest.mock import Mock, patch
from uuid import UUID

from db.model.chat_config import ChatConfigDB
from db.schema.chat_config import ChatConfig
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.chat.telegram.telegram_progress_notifier import TelegramProgressNotifier


class TelegramProgressNotifierTest(unittest.TestCase):

    chat_config: ChatConfig
    message_id: str
    mock_di: Mock
    notifier: TelegramProgressNotifier

    def setUp(self):
        self.chat_config = ChatConfig(
            chat_id = UUID(int = 1),
            external_id = "test_chat_id",
            language_iso_code = "en",
            language_name = "English",
            title = "Test Chat",
            is_private = True,
            reply_chance_percent = 100,
            chat_type = ChatConfigDB.ChatType.telegram,
        )
        self.message_id = "test_message_id"

        # Create mock DI with all necessary dependencies
        self.mock_di = Mock()
        # noinspection PyPropertyAccess
        self.mock_di.invoker_chat = self.chat_config
        # noinspection PyPropertyAccess
        self.mock_di.telegram_bot_sdk = Mock(spec = TelegramBotSDK)

        self.notifier = TelegramProgressNotifier(
            message_id = self.message_id,
            di = self.mock_di,
            auto_start = False,
        )

    # noinspection PyUnresolvedReferences
    def test_init(self):
        self.assertEqual(self.notifier._TelegramProgressNotifier__message_id, self.message_id)
        self.assertEqual(self.notifier._TelegramProgressNotifier__di, self.mock_di)

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
        self.mock_di.telegram_bot_sdk.set_status_typing.assert_called_once_with(self.chat_config.external_id)
        self.mock_di.telegram_bot_sdk.set_reaction.assert_called_once()
