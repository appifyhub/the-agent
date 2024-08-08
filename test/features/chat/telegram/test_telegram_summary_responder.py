import base64
import unittest
from unittest.mock import Mock, patch, call

from langchain_core.messages import AIMessage

from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from features.chat.telegram.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.telegram_summary_responder import respond_with_summary
from features.summarizer.raw_notes_payload import RawNotesPayload
from util.translations_cache import TranslationsCache


class TestTelegramSummaryResponder(unittest.TestCase):

    def setUp(self):
        self.chat_config_dao = Mock(spec = ChatConfigCRUD)
        self.chat_message_dao = Mock(spec = ChatMessageCRUD)
        self.telegram_bot_api = Mock(spec = TelegramBotAPI)
        self.translations = Mock(spec = TranslationsCache)
        self.payload = Mock(spec = RawNotesPayload)
        self.payload.raw_notes_b64 = base64.b64encode("Test notes".encode()).decode()

    @patch("features.chat.telegram.telegram_summary_responder.ReleaseSummarizer.execute")
    def test_successful_summary(self, mock_execute):
        mock_execute.return_value = Mock(content = "Test summary")
        self.translations.get.return_value = "Test summary"
        self.chat_config_dao.get_all.return_value = [
            {"chat_id": "123", "language_name": "English", "language_iso_code": "en"}
        ]

        result = respond_with_summary(
            self.chat_config_dao,
            self.chat_message_dao,
            self.telegram_bot_api,
            self.translations,
            self.payload,
        )

        self.assertEqual(result["summaries_created"], 1)
        self.assertEqual(result["chats_notified"], 1)
        self.assertEqual(result["chats_selected"], 1)
        self.assertEqual(result["summary"], "Test summary")
        self.telegram_bot_api.send_text_message.assert_called_once_with("123", "Test summary")
        self.chat_message_dao.save.assert_called_once()

    @patch("features.chat.telegram.telegram_summary_responder.ReleaseSummarizer")
    def test_multiple_languages(self, mock_summarizer_class):
        mock_summarizer = Mock()
        mock_summarizer.execute.return_value = AIMessage(content = "Test summary")
        mock_summarizer_class.return_value = mock_summarizer

        self.translations.get.side_effect = lambda *args: "Test summary" if args else None
        self.chat_config_dao.get_all.return_value = [
            {"chat_id": "123", "language_name": "English", "language_iso_code": "en"},
            {"chat_id": "456", "language_name": "Spanish", "language_iso_code": "es"},
        ]

        result = respond_with_summary(
            self.chat_config_dao,
            self.chat_message_dao,
            self.telegram_bot_api,
            self.translations,
            self.payload,
        )

        self.assertEqual(result["summaries_created"], 1)
        self.assertEqual(result["chats_notified"], 2)
        self.assertEqual(result["chats_selected"], 2)
        mock_summarizer_class.assert_called_once_with(
            base64.b64decode(self.payload.raw_notes_b64).decode("utf-8"),
            "English",
            "en",
        )
        mock_summarizer.execute.assert_called_once()
        self.telegram_bot_api.send_text_message.assert_any_call("123", "Test summary")
        self.telegram_bot_api.send_text_message.assert_any_call("456", "Test summary")
        self.assertEqual(self.chat_message_dao.save.call_count, 2)

    @patch("features.chat.telegram.telegram_summary_responder.ReleaseSummarizer")
    def test_summarization_failure(self, mock_summarizer_class):
        mock_summarizer = Mock()
        mock_summarizer.execute.side_effect = Exception("Summarization failed")
        mock_summarizer_class.return_value = mock_summarizer

        self.chat_config_dao.get_all.return_value = [
            {"chat_id": "123", "language_name": "English", "language_iso_code": "en"}
        ]
        self.translations.get.return_value = None  # Ensure no fallback summary

        result = respond_with_summary(
            self.chat_config_dao,
            self.chat_message_dao,
            self.telegram_bot_api,
            self.translations,
            self.payload
        )

        self.assertEqual(result["summaries_created"], 0)
        self.assertEqual(result["chats_notified"], 0)
        self.assertEqual(result["chats_selected"], 1)

        # Check that ReleaseSummarizer was called twice
        self.assertEqual(mock_summarizer_class.call_count, 2)

        # Check the calls to ReleaseSummarizer
        expected_call = call(
            base64.b64decode(self.payload.raw_notes_b64).decode("utf-8"),
            "English",
            "en"
        )
        self.assertEqual(mock_summarizer_class.call_args_list, [expected_call, expected_call])

        # Check that execute was called twice
        self.assertEqual(mock_summarizer.execute.call_count, 2)

        self.telegram_bot_api.send_text_message.assert_not_called()
        self.chat_message_dao.save.assert_not_called()

    @patch("features.chat.telegram.telegram_summary_responder.ReleaseSummarizer.execute")
    def test_notification_failure(self, mock_execute):
        mock_execute.return_value = Mock(content = "Test summary")
        self.translations.get.return_value = "Test summary"
        self.chat_config_dao.get_all.return_value = [
            {"chat_id": "123", "language_name": "English", "language_iso_code": "en"},
        ]
        self.telegram_bot_api.send_text_message.side_effect = Exception("Notification failed")

        result = respond_with_summary(
            self.chat_config_dao,
            self.chat_message_dao,
            self.telegram_bot_api,
            self.translations,
            self.payload,
        )

        self.assertEqual(result["summaries_created"], 1)
        self.assertEqual(result["chats_notified"], 0)
        self.assertEqual(result["chats_selected"], 1)
        self.chat_message_dao.save.assert_not_called()
