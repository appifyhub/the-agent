import base64
import json
import unittest
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage

from api.models.release_output_payload import ReleaseOutputPayload
from db.crud.chat_config import ChatConfigCRUD
from db.model.chat_config import ChatConfigDB
from db.schema.chat_config import ChatConfig
from features.announcements.release_summarizer import ReleaseSummarizer
from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK

# noinspection PyProtectedMember
from features.chat.telegram.telegram_summary_responder import (
    VersionChangeType,
    _strip_title_formatting,
    get_version_change_type,
    is_chat_subscribed,
    respond_with_summary,
)
from util.translations_cache import TranslationsCache


class TelegramSummaryResponderTest(unittest.TestCase):
    chat_config_dao: ChatConfigCRUD
    telegram_bot_sdk: TelegramBotSDK
    translations: TranslationsCache
    payload: ReleaseOutputPayload

    def setUp(self):
        self.chat_config_dao = Mock(spec = ChatConfigCRUD)
        self.telegram_bot_sdk = Mock(spec = TelegramBotSDK)
        self.telegram_bot_sdk.api = Mock(spec = TelegramBotAPI)
        self.translations = TranslationsCache()
        release_output_json = {
            "latest_version": "1.0.0",
            "new_target_version": "1.0.1",
            "release_quality": "stable",
            "release_notes_b64": base64.b64encode(b"notes").decode(),
        }
        self.payload = ReleaseOutputPayload(
            release_output_b64 = base64.b64encode(json.dumps(release_output_json).encode()).decode(),
        )

    def test_version_change_type_major(self):
        self.assertEqual(get_version_change_type("1.0.0", "2.0.0"), VersionChangeType.major)
        self.assertEqual(get_version_change_type("1", "2.0.0"), VersionChangeType.major)
        self.assertEqual(get_version_change_type("1.0.0", "2"), VersionChangeType.major)
        self.assertEqual(get_version_change_type("malformed", "1.0.0"), VersionChangeType.major)
        self.assertEqual(get_version_change_type("1.0.0", "malformed"), VersionChangeType.major)

    def test_version_change_type_minor(self):
        self.assertEqual(get_version_change_type("1.2.0", "1.3.0"), VersionChangeType.minor)
        self.assertEqual(get_version_change_type("1", "1.3.0"), VersionChangeType.minor)
        self.assertEqual(get_version_change_type("1.2.0", "1.3"), VersionChangeType.minor)

    def test_version_change_type_patch(self):
        self.assertEqual(get_version_change_type("1.2.3", "1.2.4"), VersionChangeType.patch)
        self.assertEqual(get_version_change_type("1.2.3", "1.2.3"), VersionChangeType.patch)
        self.assertEqual(get_version_change_type("1.2", "1.2.1"), VersionChangeType.patch)
        self.assertEqual(get_version_change_type("1", "1.0.1"), VersionChangeType.patch)

    def test_is_chat_subscribed_all(self):
        chat = self.__make_chat(ChatConfigDB.ReleaseNotifications.all)
        for change in VersionChangeType:
            self.assertTrue(is_chat_subscribed(chat, change))

    def test_is_chat_subscribed_none(self):
        chat = self.__make_chat(ChatConfigDB.ReleaseNotifications.none)
        for change in VersionChangeType:
            self.assertFalse(is_chat_subscribed(chat, change))

    def test_is_chat_subscribed_major(self):
        chat = self.__make_chat(ChatConfigDB.ReleaseNotifications.major)
        self.assertTrue(is_chat_subscribed(chat, VersionChangeType.major))
        self.assertFalse(is_chat_subscribed(chat, VersionChangeType.minor))
        self.assertFalse(is_chat_subscribed(chat, VersionChangeType.patch))

    def test_is_chat_subscribed_minor(self):
        chat = self.__make_chat(ChatConfigDB.ReleaseNotifications.minor)
        self.assertTrue(is_chat_subscribed(chat, VersionChangeType.major))
        self.assertTrue(is_chat_subscribed(chat, VersionChangeType.minor))
        self.assertFalse(is_chat_subscribed(chat, VersionChangeType.patch))

    @patch("features.chat.telegram.telegram_summary_responder.base64.b64decode")
    def test_decoding_failure(self, mock_b64decode):
        mock_b64decode.side_effect = Exception("decode error")
        payload = ReleaseOutputPayload(release_output_b64 = "invalid")
        result = respond_with_summary(self.chat_config_dao, self.telegram_bot_sdk, self.translations, payload)
        self.assertIn("Failed to decode release notes", result["summary"])
        self.assertEqual(result["summaries_created"], 0)

    @patch("features.chat.telegram.telegram_summary_responder.ReleaseSummarizer.execute")
    def test_successful_summary(self, mock_execute):
        mock_execute.return_value = Mock(content = "Test summary")
        self.translations.save("Test summary")
        self.chat_config_dao.get_all.return_value = [self.__make_chat_db()]
        result = respond_with_summary(self.chat_config_dao, self.telegram_bot_sdk, self.translations, self.payload)
        self.assertEqual(result["chats_notified"], 1)
        # noinspection PyUnresolvedReferences
        self.telegram_bot_sdk.send_text_message.assert_called_once_with("1234", "Test summary")

    @patch("features.chat.telegram.telegram_summary_responder.ReleaseSummarizer")
    def test_multiple_languages(self, mock_summarizer_cls):
        mock_summarizer = Mock(spec = ReleaseSummarizer)
        mock_summarizer.execute.return_value = AIMessage(content = "Summary")
        mock_summarizer_cls.return_value = mock_summarizer
        self.chat_config_dao.get_all.return_value = [
            self.__make_chat_db(chat_id = "123", lang_name = "English", lang_iso = "en"),
            self.__make_chat_db(chat_id = "456", lang_name = "Spanish", lang_iso = "es"),
        ]
        result = respond_with_summary(self.chat_config_dao, self.telegram_bot_sdk, self.translations, self.payload)
        self.assertEqual(result["chats_notified"], 2)
        self.assertEqual(result["summaries_created"], 2)

    @patch("features.chat.telegram.telegram_summary_responder.ReleaseSummarizer.execute")
    def test_telegram_send_failure(self, mock_execute):
        mock_execute.return_value = Mock(content = "Summary")
        self.chat_config_dao.get_all.return_value = [self.__make_chat_db()]
        self.telegram_bot_sdk.send_text_message.side_effect = Exception("fail")
        result = respond_with_summary(self.chat_config_dao, self.telegram_bot_sdk, self.translations, self.payload)
        self.assertEqual(result["chats_notified"], 0)

    @patch("features.chat.telegram.telegram_summary_responder.ReleaseSummarizer.execute")
    def test_no_eligible_chats(self, mock_execute):
        mock_execute.return_value = Mock(content = "Summary")
        self.chat_config_dao.get_all.return_value = []
        result = respond_with_summary(self.chat_config_dao, self.telegram_bot_sdk, self.translations, self.payload)
        self.assertEqual(result["chats_eligible"], 0)

    @patch("features.chat.telegram.telegram_summary_responder.ReleaseSummarizer")
    def test_all_translations(self, mock_summarizer_cls):
        mock_sum = Mock(spec = ReleaseSummarizer)
        mock_sum.execute.return_value = Mock(content = "Gen summary")
        mock_summarizer_cls.return_value = mock_sum
        self.chat_config_dao.get_all.return_value = [
            self.__make_chat_db(chat_id = "123", lang_name = "English", lang_iso = "en"),
            self.__make_chat_db(chat_id = "456", lang_name = "Spanish", lang_iso = "es"),
            self.__make_chat_db(chat_id = "789", lang_name = "Greek", lang_iso = "gr"),
            self.__make_chat_db(chat_id = "sss", lang_name = "Spanish", lang_iso = "es"),
            self.__make_chat_db(chat_id = "eee", lang_name = "English", lang_iso = "en"),
        ]
        result = respond_with_summary(self.chat_config_dao, self.telegram_bot_sdk, TranslationsCache(), self.payload)
        self.assertEqual(result["chats_eligible"], 5)
        self.assertEqual(result["chats_notified"], 5)
        self.assertEqual(result["summaries_created"], 3)

    @patch("features.chat.telegram.telegram_summary_responder.ReleaseSummarizer")
    def test_summarization_failure(self, mock_summarizer_cls):
        mock_sum = Mock(spec = ReleaseSummarizer)
        mock_sum.execute.side_effect = Exception("boom")
        mock_summarizer_cls.return_value = mock_sum
        self.chat_config_dao.get_all.return_value = [self.__make_chat_db()]
        result = respond_with_summary(self.chat_config_dao, self.telegram_bot_sdk, self.translations, self.payload)
        self.assertEqual(result["chats_notified"], 0)
        self.assertIsNotNone(result["summary"])

    def test_strip_title_formatting(self):
        self.assertEqual(_strip_title_formatting("# Title\nContent"), "Title\nContent")
        self.assertEqual(_strip_title_formatting("##  Title\nContent"), "Title\nContent")
        self.assertEqual(_strip_title_formatting("###Title\nContent"), "Title\nContent")
        self.assertEqual(_strip_title_formatting("#    Title"), "Title")
        self.assertEqual(_strip_title_formatting("No title here"), "No title here")
        self.assertEqual(_strip_title_formatting("#######   Title"), "Title")
        self.assertEqual(_strip_title_formatting("#Title"), "Title")
        self.assertEqual(_strip_title_formatting("##\tTitle"), "Title")
        self.assertEqual(_strip_title_formatting("###   "), "")

    @staticmethod
    def __make_chat_db(
        notifications: ChatConfigDB.ReleaseNotifications = ChatConfigDB.ReleaseNotifications.all,
        chat_id: str = "1234",
        lang_name: str = "English",
        lang_iso: str = "en",
    ) -> ChatConfigDB:
        return ChatConfigDB(
            chat_id = chat_id,
            language_name = lang_name,
            language_iso_code = lang_iso,
            title = "Chat Title",
            is_private = True,
            reply_chance_percent = 100,
            release_notifications = notifications,
        )

    @staticmethod
    def __make_chat(
        notifications: ChatConfigDB.ReleaseNotifications = ChatConfigDB.ReleaseNotifications.all,
        chat_id: str = "1234",
        lang_name: str = "English",
        lang_iso: str = "en",
    ) -> ChatConfig:
        return ChatConfig.model_validate(
            ChatConfigDB(
                chat_id = chat_id,
                language_name = lang_name,
                language_iso_code = lang_iso,
                title = "Chat Title",
                is_private = True,
                reply_chance_percent = 100,
                release_notifications = notifications,
            ),
        )
