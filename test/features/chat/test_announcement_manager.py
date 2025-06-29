import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

from langchain_core.messages import AIMessage

from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.user import User
from features.chat.announcement_manager import AnnouncementManager
from features.chat.telegram.sdk.telegram_bot_api import TelegramBotAPI
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from util.translations_cache import TranslationsCache


@patch("features.chat.announcement_manager.ChatAnthropic")
class AnnouncementManagerTest(unittest.TestCase):
    raw_announcement: str
    invoker_user_id: UUID
    user: User
    mock_user_dao: UserCRUD
    mock_chat_config_dao: ChatConfigCRUD
    mock_chat_message_dao: ChatMessageCRUD
    mock_sponsorship_dao: SponsorshipCRUD
    mock_telegram_bot_sdk: TelegramBotSDK
    mock_translations: TranslationsCache

    def setUp(self):
        self.raw_announcement = "Scheduled maintenance on Friday"
        self.invoker_user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        self.user = User(
            id = self.invoker_user_id,
            full_name = "Test Developer",
            telegram_username = "test_dev",
            telegram_chat_id = "dev_chat_id",
            telegram_user_id = 1,
            open_ai_key = "test_api_key",
            anthropic_key = "test_anthropic_key",
            group = UserDB.Group.developer,
            created_at = datetime.now().date(),
        )
        self.user.group = UserDB.Group.developer
        self.mock_user_dao = MagicMock(spec = UserCRUD)
        self.mock_chat_config_dao = MagicMock(spec = ChatConfigCRUD)
        self.mock_chat_message_dao = MagicMock(spec = ChatMessageCRUD)
        self.mock_sponsorship_dao = MagicMock(spec = SponsorshipCRUD)
        self.mock_telegram_bot_sdk = MagicMock(spec = TelegramBotSDK)
        self.mock_telegram_bot_sdk.api = MagicMock(spec = TelegramBotAPI)
        self.mock_translations = MagicMock(spec = TranslationsCache)

        self.mock_user_dao.get.return_value = self.user
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

    # noinspection PyUnusedLocal
    def test_init_success(self, mock_chat_anthropic):
        manager = AnnouncementManager(
            self.raw_announcement,
            str(self.invoker_user_id),
            None,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_chat_message_dao,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            self.mock_translations,
        )
        self.assertIsInstance(manager, AnnouncementManager)

    # noinspection PyUnusedLocal
    def test_init_user_not_found(self, mock_chat_anthropic):
        self.mock_user_dao.get.return_value = None
        with self.assertRaises(ValueError):
            AnnouncementManager(
                self.raw_announcement,
                str(self.invoker_user_id),
                None,
                self.mock_user_dao,
                self.mock_chat_config_dao,
                self.mock_chat_message_dao,
                self.mock_sponsorship_dao,
                self.mock_telegram_bot_sdk,
                self.mock_translations,
            )

    # noinspection PyUnusedLocal
    def test_init_user_not_developer(self, mock_chat_anthropic):
        self.user.group = UserDB.Group.standard
        with self.assertRaises(ValueError):
            AnnouncementManager(
                self.raw_announcement,
                str(self.invoker_user_id),
                None,
                self.mock_user_dao,
                self.mock_chat_config_dao,
                self.mock_chat_message_dao,
                self.mock_sponsorship_dao,
                self.mock_telegram_bot_sdk,
                self.mock_translations,
            )

    def test_execute_success(self, mock_chat_anthropic):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Translated announcement")
        mock_chat_anthropic.return_value = mock_llm

        self.mock_chat_config_dao.get_all.return_value = [
            {"chat_id": "123", "language_name": "English", "language_iso_code": "en"},
            {"chat_id": "456", "language_name": "Spanish", "language_iso_code": "es"},
        ]
        self.mock_translations.get.side_effect = [None, "Translated announcement"]
        self.mock_translations.save.return_value = "Translated announcement"

        manager = AnnouncementManager(
            self.raw_announcement,
            str(self.invoker_user_id),
            None,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_chat_message_dao,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            self.mock_translations,
        )
        result = manager.execute()

        self.assertEqual(result["summaries_created"], 2)
        self.assertEqual(result["chats_notified"], 2)
        self.assertEqual(result["chats_selected"], 2)
        # noinspection PyUnresolvedReferences
        self.mock_telegram_bot_sdk.send_text_message.assert_any_call("123", "Translated announcement")
        # noinspection PyUnresolvedReferences
        self.mock_telegram_bot_sdk.send_text_message.assert_any_call("456", "Translated announcement")
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.mock_chat_message_dao.save.call_count, 2)

    def test_execute_translation_failure(self, mock_chat_anthropic):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("Translation failed")
        mock_chat_anthropic.return_value = mock_llm

        self.mock_chat_config_dao.get_all.return_value = [
            {"chat_id": "123", "language_name": "English", "language_iso_code": "en"},
        ]
        self.mock_translations.get.return_value = None

        manager = AnnouncementManager(
            self.raw_announcement,
            str(self.invoker_user_id),
            None,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_chat_message_dao,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            self.mock_translations,
        )
        result = manager.execute()

        self.assertEqual(result["summaries_created"], 0)
        self.assertEqual(result["chats_notified"], 0)
        self.assertEqual(result["chats_selected"], 1)
        # noinspection PyUnresolvedReferences
        self.mock_telegram_bot_sdk.send_text_message.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_chat_message_dao.save.assert_not_called()

    def test_execute_notification_failure(self, mock_chat_anthropic):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Translated announcement")
        mock_chat_anthropic.return_value = mock_llm

        self.mock_chat_config_dao.get_all.return_value = [
            {"chat_id": "123", "language_name": "English", "language_iso_code": "en"},
        ]
        self.mock_translations.get.return_value = "Translated announcement"
        self.mock_telegram_bot_sdk.send_text_message.side_effect = Exception("Notification failed")

        manager = AnnouncementManager(
            self.raw_announcement,
            str(self.invoker_user_id),
            None,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_chat_message_dao,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            self.mock_translations,
        )
        result = manager.execute()

        self.assertEqual(result["summaries_created"], 1)
        self.assertEqual(result["chats_notified"], 0)
        self.assertEqual(result["chats_selected"], 1)
        # noinspection PyUnresolvedReferences
        self.mock_telegram_bot_sdk.send_text_message.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_chat_message_dao.save.assert_not_called()

    def test_execute_no_chats(self, mock_chat_anthropic):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Translated announcement")
        mock_chat_anthropic.return_value = mock_llm
        self.mock_chat_config_dao.get_all.return_value = []

        manager = AnnouncementManager(
            self.raw_announcement,
            str(self.invoker_user_id),
            None,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_chat_message_dao,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            self.mock_translations,
        )
        result = manager.execute()

        self.assertEqual(result["summaries_created"], 1)
        self.assertEqual(result["chats_notified"], 0)
        self.assertEqual(result["chats_selected"], 0)
        # noinspection PyUnresolvedReferences
        self.mock_telegram_bot_sdk.send_text_message.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_chat_message_dao.save.assert_not_called()

    def test_targeted_announcement_success(self, mock_chat_anthropic):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Translated announcement")
        mock_chat_anthropic.return_value = mock_llm

        target_user = User(
            id = UUID("223e4567-e89b-12d3-a456-426614174001"),
            full_name = "Target User",
            telegram_username = "target_user",
            telegram_chat_id = "target_chat_id",
            telegram_user_id = 2,
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.mock_user_dao.get_by_telegram_username.return_value = target_user
        self.mock_chat_config_dao.get.return_value = {
            "chat_id": "target_chat_id",
            "language_name": "English",
            "language_iso_code": "en",
        }
        self.mock_translations.get.return_value = "Translated announcement"

        manager = AnnouncementManager(
            self.raw_announcement,
            str(self.invoker_user_id),
            "target_user",
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_chat_message_dao,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            self.mock_translations,
        )
        result = manager.execute()

        self.assertEqual(result["summaries_created"], 1)
        self.assertEqual(result["chats_notified"], 1)
        self.assertEqual(result["chats_selected"], 1)
        # noinspection PyUnresolvedReferences
        self.mock_telegram_bot_sdk.send_text_message.assert_called_once_with(
            "target_chat_id",
            "Translated announcement",
        )
        # noinspection PyUnresolvedReferences
        self.mock_chat_message_dao.save.assert_called_once()

    # noinspection PyUnusedLocal
    def test_targeted_announcement_invalid_username(self, mock_chat_anthropic):
        self.mock_user_dao.get_by_telegram_username.return_value = None

        with self.assertRaises(ValueError) as context:
            AnnouncementManager(
                self.raw_announcement,
                str(self.invoker_user_id),
                "nonexistent_user",
                self.mock_user_dao,
                self.mock_chat_config_dao,
                self.mock_chat_message_dao,
                self.mock_sponsorship_dao,
                self.mock_telegram_bot_sdk,
                self.mock_translations,
            )

        self.assertIn("Target user 'nonexistent_user' not found", str(context.exception))

    # noinspection PyUnusedLocal
    def test_targeted_announcement_no_chat_id(self, mock_chat_anthropic):
        target_user = User(
            id = UUID("223e4567-e89b-12d3-a456-426614174001"),
            full_name = "Target User",
            telegram_username = "target_user",
            telegram_chat_id = None,
            telegram_user_id = 2,
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.mock_user_dao.get_by_telegram_username.return_value = target_user

        with self.assertRaises(ValueError) as context:
            AnnouncementManager(
                self.raw_announcement,
                str(self.invoker_user_id),
                "target_user",
                self.mock_user_dao,
                self.mock_chat_config_dao,
                self.mock_chat_message_dao,
                self.mock_sponsorship_dao,
                self.mock_telegram_bot_sdk,
                self.mock_translations,
            )

        self.assertIn("Target user 'target_user' has no private chat ID yet", str(context.exception))

    # noinspection PyUnusedLocal
    def test_targeted_announcement_chat_not_found(self, mock_chat_anthropic):
        target_user = User(
            id = UUID("223e4567-e89b-12d3-a456-426614174001"),
            full_name = "Target User",
            telegram_username = "target_user",
            telegram_chat_id = "nonexistent_chat_id",
            telegram_user_id = 2,
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.mock_user_dao.get_by_telegram_username.return_value = target_user
        self.mock_chat_config_dao.get.return_value = None

        with self.assertRaises(ValueError) as context:
            AnnouncementManager(
                self.raw_announcement,
                str(self.invoker_user_id),
                "target_user",
                self.mock_user_dao,
                self.mock_chat_config_dao,
                self.mock_chat_message_dao,
                self.mock_sponsorship_dao,
                self.mock_telegram_bot_sdk,
                self.mock_translations,
            )

        self.assertIn("Target chat 'nonexistent_chat_id' not found", str(context.exception))
