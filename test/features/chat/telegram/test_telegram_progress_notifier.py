import unittest
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID

from db.model.chat_config import ChatConfigDB
from db.schema.chat_config import ChatConfig
from features.chat.chat_progress_notifier import ChatProgressNotifier
from features.integrations.platform_bot_sdk import PlatformBotSDK


class ChatProgressNotifierTest(unittest.TestCase):

    chat_config: ChatConfig
    message_id: str
    mock_di: Mock
    notifier: ChatProgressNotifier

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
        self.mock_di.require_invoker_chat = MagicMock(return_value = self.chat_config)
        # noinspection PyPropertyAccess
        self.mock_di.platform_bot_sdk = Mock(return_value = Mock(spec = PlatformBotSDK))
        self.mock_di.require_invoker_chat_type = MagicMock(return_value = ChatConfigDB.ChatType.telegram)

        self.notifier = ChatProgressNotifier(
            message_id = self.message_id,
            di = self.mock_di,
            auto_start = False,
        )

    # noinspection PyUnresolvedReferences
    def test_init(self):
        self.assertEqual(self.notifier._ChatProgressNotifier__message_id, self.message_id)
        self.assertEqual(self.notifier._ChatProgressNotifier__di, self.mock_di)

    @patch("features.chat.chat_progress_notifier.Thread")
    def test_start(self, mock_thread):
        self.notifier.start()
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

    @patch("features.chat.chat_progress_notifier.Thread")
    def test_stop(self, mock_thread):
        self.notifier.start()
        self.notifier.stop()
        mock_thread.return_value.join.assert_called_once_with(timeout = 1)

    @patch("features.chat.chat_progress_notifier.time.time")
    def test_send_reaction(self, mock_time):
        mock_time.return_value = 100
        mock_platform_sdk = Mock(spec = PlatformBotSDK)
        self.mock_di.platform_bot_sdk.return_value = mock_platform_sdk
        # noinspection PyUnresolvedReferences
        self.notifier._ChatProgressNotifier__send_reaction()
        mock_platform_sdk.set_chat_action.assert_called_once()
        mock_platform_sdk.set_reaction.assert_called_once()
