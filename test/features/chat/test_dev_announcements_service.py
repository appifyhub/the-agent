import unittest
from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID

from langchain_core.messages import AIMessage
from pydantic import SecretStr

from db.model.chat_config import ChatConfigDB
from db.model.user import UserDB
from db.schema.user import User
from features.chat.dev_announcements_service import DevAnnouncementsService
from features.external_tools.tool_choice_resolver import ConfiguredTool


class DevAnnouncementsServiceTest(unittest.TestCase):

    raw_announcement: str
    invoker_user_id: UUID
    user: User
    mock_di: MagicMock
    mock_configured_tool: ConfiguredTool

    def setUp(self):
        self.raw_announcement = "Test announcement"
        self.invoker_user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        self.user = User(
            id = self.invoker_user_id,
            full_name = "Test User",
            telegram_username = "test_username",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = SecretStr("test_api_key"),
            replicate_key = SecretStr("test_replicate_key"),
            anthropic_key = SecretStr("test_anthropic_key"),
            group = UserDB.Group.developer,
            created_at = datetime.now().date(),
        )

        # Mock DI
        self.mock_di = MagicMock()
        self.mock_di.invoker = self.user
        self.mock_di.chat_langchain_model.return_value = MagicMock()
        self.mock_di.user_crud.get_by_telegram_username.return_value = None
        self.mock_di.chat_config_crud.get.return_value = None
        self.mock_di.chat_config_crud.get_all.return_value = []
        self.mock_di.telegram_bot_sdk.send_text_message.return_value = {"result": {"message_id": 123}}
        self.mock_di.chat_message_crud.save.return_value = MagicMock()
        self.mock_di.translations_cache.get.return_value = "Translated announcement"
        self.mock_di.translations_cache.save.return_value = "Translated announcement"

        # Mock configured tool
        # noinspection PyTypeChecker
        self.mock_configured_tool = MagicMock(spec = ConfiguredTool)

    @staticmethod
    def __create_mock_chat_config(chat_id: str, language: str = "en"):
        """Helper to create a properly mocked ChatConfig object"""
        mock_chat = MagicMock()
        mock_chat.chat_id = chat_id
        mock_chat.language_iso_code = language
        mock_chat.language_name = "English" if language == "en" else "Spanish"
        mock_chat.title = f"Chat {chat_id}"
        mock_chat.is_private = True
        mock_chat.reply_chance_percent = 100
        mock_chat.release_notifications = ChatConfigDB.ReleaseNotifications.all
        return mock_chat

    def test_init_success(self):
        service = DevAnnouncementsService(
            self.raw_announcement,
            None,
            self.mock_configured_tool,
            self.mock_di,
        )
        self.assertIsInstance(service, DevAnnouncementsService)

    def test_init_user_not_found(self):
        self.mock_di.invoker.group = UserDB.Group.standard
        with self.assertRaises(ValueError):
            DevAnnouncementsService(
                self.raw_announcement,
                None,
                self.mock_configured_tool,
                self.mock_di,
            )

    def test_init_user_not_developer(self):
        self.user.group = UserDB.Group.standard
        self.mock_di.invoker = self.user
        with self.assertRaises(ValueError):
            DevAnnouncementsService(
                self.raw_announcement,
                None,
                self.mock_configured_tool,
                self.mock_di,
            )

    def test_execute_success(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined announcement")
        self.mock_di.chat_langchain_model.return_value = mock_llm

        self.mock_di.chat_config_crud.get_all.return_value = [
            self.__create_mock_chat_config("chat1", "en"),
            self.__create_mock_chat_config("chat2", "es"),
        ]

        service = DevAnnouncementsService(
            self.raw_announcement,
            None,
            self.mock_configured_tool,
            self.mock_di,
        )
        result = service.execute()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["chats_selected"], 2)
        self.assertEqual(result["chats_notified"], 2)
        self.assertEqual(result["summaries_created"], 1)
        mock_llm.invoke.assert_called_once()

    def test_execute_translation_failure(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined announcement")
        self.mock_di.chat_langchain_model.return_value = mock_llm

        self.mock_di.chat_config_crud.get_all.return_value = [
            self.__create_mock_chat_config("chat1", "en"),
        ]
        self.mock_di.translations_cache.get.return_value = None  # Force translation attempt
        self.mock_di.translations_cache.save.side_effect = Exception("Translation failed")

        service = DevAnnouncementsService(
            self.raw_announcement,
            None,
            self.mock_configured_tool,
            self.mock_di,
        )
        result = service.execute()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["chats_selected"], 1)
        self.assertEqual(result["chats_notified"], 0)
        self.assertEqual(result["summaries_created"], 0)

    def test_execute_notification_failure(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined announcement")
        self.mock_di.chat_langchain_model.return_value = mock_llm

        self.mock_di.chat_config_crud.get_all.return_value = [
            self.__create_mock_chat_config("chat1", "en"),
        ]
        self.mock_di.telegram_bot_sdk.send_text_message.side_effect = Exception("Notification failed")

        service = DevAnnouncementsService(
            self.raw_announcement,
            None,
            self.mock_configured_tool,
            self.mock_di,
        )
        result = service.execute()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["chats_selected"], 1)
        self.assertEqual(result["chats_notified"], 0)
        self.assertEqual(result["summaries_created"], 1)

    def test_execute_no_chats(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined announcement")
        self.mock_di.chat_langchain_model.return_value = mock_llm

        self.mock_di.chat_config_crud.get_all.return_value = []

        service = DevAnnouncementsService(
            self.raw_announcement,
            None,
            self.mock_configured_tool,
            self.mock_di,
        )
        result = service.execute()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["chats_selected"], 0)
        self.assertEqual(result["chats_notified"], 0)
        self.assertEqual(result["summaries_created"], 1)

    def test_targeted_announcement_success(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined announcement")
        self.mock_di.chat_langchain_model.return_value = mock_llm

        target_user = User(
            id = UUID("223e4567-e89b-12d3-a456-426614174000"),
            full_name = "Target User",
            telegram_username = "target_user",
            telegram_chat_id = "target_chat_id",
            telegram_user_id = 2,
            open_ai_key = SecretStr("test_api_key"),
            replicate_key = SecretStr("test_replicate_key"),
            anthropic_key = SecretStr("test_anthropic_key"),
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )

        self.mock_di.user_crud.get_by_telegram_username.return_value = target_user
        self.mock_di.chat_config_crud.get.return_value = self.__create_mock_chat_config("target_chat_id", "en")

        service = DevAnnouncementsService(
            self.raw_announcement,
            "target_user",
            self.mock_configured_tool,
            self.mock_di,
        )
        result = service.execute()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["chats_selected"], 1)
        self.assertEqual(result["chats_notified"], 1)
        self.assertEqual(result["summaries_created"], 1)

    def test_targeted_announcement_invalid_username(self):
        self.mock_di.user_crud.get_by_telegram_username.return_value = None

        with self.assertRaises(ValueError) as context:
            DevAnnouncementsService(
                self.raw_announcement,
                "nonexistent_user",
                self.mock_configured_tool,
                self.mock_di,
            )

        self.assertIn("Target user 'nonexistent_user' not found", str(context.exception))

    def test_targeted_announcement_no_chat_id(self):
        target_user = User(
            id = UUID("223e4567-e89b-12d3-a456-426614174000"),
            full_name = "Target User",
            telegram_username = "target_user",
            telegram_chat_id = None,
            telegram_user_id = 2,
            open_ai_key = SecretStr("test_api_key"),
            replicate_key = SecretStr("test_replicate_key"),
            anthropic_key = SecretStr("test_anthropic_key"),
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )

        self.mock_di.user_crud.get_by_telegram_username.return_value = target_user

        with self.assertRaises(ValueError) as context:
            DevAnnouncementsService(
                self.raw_announcement,
                "target_user",
                self.mock_configured_tool,
                self.mock_di,
            )

        self.assertIn("Target user 'target_user' has no private chat ID yet", str(context.exception))

    def test_targeted_announcement_chat_not_found(self):
        target_user = User(
            id = UUID("223e4567-e89b-12d3-a456-426614174000"),
            full_name = "Target User",
            telegram_username = "target_user",
            telegram_chat_id = "target_chat_id",
            telegram_user_id = 2,
            open_ai_key = SecretStr("test_api_key"),
            replicate_key = SecretStr("test_replicate_key"),
            anthropic_key = SecretStr("test_anthropic_key"),
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )

        self.mock_di.user_crud.get_by_telegram_username.return_value = target_user
        self.mock_di.chat_config_crud.get.return_value = None

        with self.assertRaises(ValueError) as context:
            DevAnnouncementsService(
                self.raw_announcement,
                "target_user",
                self.mock_configured_tool,
                self.mock_di,
            )

        self.assertIn("Target chat 'target_chat_id' not found", str(context.exception))
