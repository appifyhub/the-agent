import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from features.chat.telegram.telegram_progress_notifier import TelegramProgressNotifier, ChatConfig


class TelegramProgressNotifierTest(unittest.TestCase):

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
        self.mock_bot_api = Mock()
        self.mock_chat_message_dao = Mock()

        self.mock_chat_anthropic = Mock()
        self.mock_chat_anthropic.invoke.return_value = Mock(content = "Mocked AI response")

        self.chat_anthropic_patcher = patch(
            "features.chat.telegram.telegram_progress_notifier.ChatAnthropic",
            return_value = self.mock_chat_anthropic
        )
        self.chat_anthropic_patcher.start()

        self.notifier = TelegramProgressNotifier(
            chat_config = self.chat_config,
            message_id = self.message_id,
            bot_api = self.mock_bot_api,
            chat_message_dao = self.mock_chat_message_dao,
            auto_start = False
        )

    def tearDown(self):
        self.chat_anthropic_patcher.stop()

    # noinspection PyUnresolvedReferences
    def test_init(self):
        self.assertEqual(self.notifier._TelegramProgressNotifier__chat_config, self.chat_config)
        self.assertEqual(self.notifier._TelegramProgressNotifier__message_id, self.message_id)
        self.assertIsNotNone(self.notifier._TelegramProgressNotifier__llm)

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
        self.mock_bot_api.set_status_typing.assert_called_once_with(self.chat_config.chat_id)
        self.mock_bot_api.set_reaction.assert_called_once()

    @patch("features.chat.telegram.telegram_progress_notifier.time.time")
    @patch("features.chat.telegram.telegram_progress_notifier.datetime")
    def test_send_message(self, mock_datetime, mock_time):
        mock_time.return_value = 100
        mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)

        # Call the method
        # noinspection PyUnresolvedReferences
        self.notifier._TelegramProgressNotifier__send_message()

        # Collect information about method calls
        bot_api_calls = self.mock_bot_api.method_calls
        chat_message_dao_calls = self.mock_chat_message_dao.method_calls
        chat_anthropic_calls = self.mock_chat_anthropic.method_calls

        # Assert on the collected information
        self.assertGreater(len(bot_api_calls), 0, "No methods were called on TelegramBotAPI")
        self.assertEqual(len(chat_message_dao_calls), 0, "Unexpected calls to ChatMessageCRUD")
        self.assertEqual(len(chat_anthropic_calls), 1, "Expected one call to ChatAnthropic")

        # Check specific method calls
        self.mock_bot_api.set_status_uploading_image.assert_called_once_with(self.chat_config.chat_id)
        self.mock_chat_anthropic.invoke.assert_called_once()

        # Check that send_text_message and save were not called
        self.mock_bot_api.send_text_message.assert_not_called()
        self.mock_chat_message_dao.save.assert_not_called()

        # If we want to check the content of the ChatAnthropic call:
        chat_anthropic_call = chat_anthropic_calls[0]
        self.assertEqual(chat_anthropic_call[0], 'invoke', "Unexpected method called on ChatAnthropic")
        self.assertIsInstance(chat_anthropic_call[1][0], list, "Expected first argument to invoke to be a list")

        # Assert that at least one method was called overall
        total_calls = len(bot_api_calls) + len(chat_message_dao_calls) + len(chat_anthropic_calls)
        self.assertGreater(total_calls, 0, "No methods were called on any mocked object")
