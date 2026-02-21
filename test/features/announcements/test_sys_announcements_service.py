import unittest
from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock
from uuid import UUID

from pydantic import SecretStr

from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.model.chat_config import ChatConfigDB
from db.model.chat_message import ChatMessageDB
from db.model.user import UserDB
from db.schema.user import User
from di.di import DI
from features.announcements.sys_announcements_service import WHATSAPP_MESSAGING_WINDOW_HOURS, SysAnnouncementsService
from features.external_tools.configured_tool import ConfiguredTool


class SysAnnouncementsServicePlatformSelectionTest(unittest.TestCase):

    mock_di: DI
    mock_user: User
    mock_configured_tool: ConfiguredTool

    def setUp(self):
        self.mock_di = Mock(spec = DI)
        self.mock_configured_tool = Mock(spec = ConfiguredTool)

        # Create test user
        user_id = UUID(int = 1)
        self.mock_user = User(
            id = user_id,
            created_at = date.today(),
            full_name = "Test User",
            telegram_user_id = 12345,
            telegram_chat_id = "telegram_chat_123",
            whatsapp_user_id = "whatsapp_user_123",
            whatsapp_phone_number = SecretStr("+1234567890"),
            group = UserDB.Group.standard,
        )

        # Mock DI invoker to return our test user
        self.mock_di.invoker = self.mock_user

        # Mock chat_config_crud
        self.mock_di.chat_config_crud = Mock(spec = ChatConfigCRUD)

        # Mock chat_message_crud
        self.mock_di.chat_message_crud = Mock(spec = ChatMessageCRUD)

        # Mock authorization_service
        self.mock_di.authorization_service = Mock()
        self.mock_di.authorization_service.validate_chat = lambda chat: chat

        # Mock chat_langchain_model
        self.mock_di.chat_langchain_model = Mock()

    def _create_chat_config(self, chat_type: ChatConfigDB.ChatType, external_id: str) -> ChatConfigDB:
        return ChatConfigDB(
            chat_id = UUID(int = hash(external_id) % (2**32)),
            external_id = external_id,
            title = f"Test {chat_type.value} Chat",
            is_private = True,
            reply_chance_percent = 100,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
            language_name = "English",
            language_iso_code = "en",
            media_mode = ChatConfigDB.MediaMode.photo,
            use_about_me = True,
            chat_type = chat_type,
        )

    def _create_message(self, chat_id: UUID, author_id: UUID, sent_at: datetime) -> ChatMessageDB:
        return ChatMessageDB(
            chat_id = chat_id,
            author_id = author_id,
            message_id = f"msg_{sent_at.timestamp()}",
            sent_at = sent_at,
            text = "Test message",
        )

    def test_whatsapp_within_24h_window(self):
        """WhatsApp chat with recent message (< 24h) should be selected."""
        whatsapp_chat = self._create_chat_config(ChatConfigDB.ChatType.whatsapp, "whatsapp_user_123")
        recent_message = self._create_message(
            whatsapp_chat.chat_id,
            self.mock_user.id,
            datetime.now(UTC) - timedelta(hours = 12),
        )

        self.mock_di.chat_config_crud.get_by_external_identifiers = Mock(side_effect = lambda external_id, chat_type: (
            whatsapp_chat if chat_type == ChatConfigDB.ChatType.whatsapp else None
        ))
        self.mock_di.chat_message_crud.get_latest_chat_messages = Mock(return_value = [recent_message])

        service = SysAnnouncementsService("Test", None, self.mock_configured_tool, self.mock_di)
        resolved_chat = service._SysAnnouncementsService__resolved_chat

        self.assertEqual(resolved_chat.chat_type, ChatConfigDB.ChatType.whatsapp)
        self.assertEqual(resolved_chat.external_id, "whatsapp_user_123")

    def test_whatsapp_outside_24h_window(self):
        """WhatsApp chat with old message (> 24h) should not be selected when no Telegram available."""
        whatsapp_chat = self._create_chat_config(ChatConfigDB.ChatType.whatsapp, "whatsapp_user_123")
        old_message = self._create_message(
            whatsapp_chat.chat_id,
            self.mock_user.id,
            datetime.now(UTC) - timedelta(hours = WHATSAPP_MESSAGING_WINDOW_HOURS + 1),
        )

        self.mock_di.chat_config_crud.get_by_external_identifiers = Mock(side_effect = lambda external_id, chat_type: (
            whatsapp_chat if chat_type == ChatConfigDB.ChatType.whatsapp else None
        ))
        self.mock_di.chat_message_crud.get_latest_chat_messages = Mock(return_value = [old_message])

        with self.assertRaises(ValueError) as context:
            SysAnnouncementsService("Test", None, self.mock_configured_tool, self.mock_di)

        self.assertIn("Cannot resolve target chat", str(context.exception))

    def test_telegram_only(self):
        """Only Telegram available should select Telegram."""
        telegram_chat = self._create_chat_config(ChatConfigDB.ChatType.telegram, "telegram_chat_123")
        telegram_message = self._create_message(
            telegram_chat.chat_id,
            self.mock_user.id,
            datetime.now(UTC) - timedelta(hours = 1),
        )

        self.mock_di.chat_config_crud.get_by_external_identifiers = Mock(side_effect = lambda external_id, chat_type: (
            telegram_chat if chat_type == ChatConfigDB.ChatType.telegram else None
        ))
        self.mock_di.chat_message_crud.get_latest_chat_messages = Mock(return_value = [telegram_message])

        service = SysAnnouncementsService("Test", None, self.mock_configured_tool, self.mock_di)
        resolved_chat = service._SysAnnouncementsService__resolved_chat

        self.assertEqual(resolved_chat.chat_type, ChatConfigDB.ChatType.telegram)
        self.assertEqual(resolved_chat.external_id, "telegram_chat_123")

    def test_whatsapp_only_within_24h(self):
        """Only WhatsApp available with recent message should select WhatsApp."""
        whatsapp_chat = self._create_chat_config(ChatConfigDB.ChatType.whatsapp, "whatsapp_user_123")
        recent_message = self._create_message(
            whatsapp_chat.chat_id,
            self.mock_user.id,
            datetime.now(UTC) - timedelta(hours = 6),
        )

        self.mock_di.chat_config_crud.get_by_external_identifiers = Mock(side_effect = lambda external_id, chat_type: (
            whatsapp_chat if chat_type == ChatConfigDB.ChatType.whatsapp else None
        ))
        self.mock_di.chat_message_crud.get_latest_chat_messages = Mock(return_value = [recent_message])

        service = SysAnnouncementsService("Test", None, self.mock_configured_tool, self.mock_di)
        resolved_chat = service._SysAnnouncementsService__resolved_chat

        self.assertEqual(resolved_chat.chat_type, ChatConfigDB.ChatType.whatsapp)

    def test_both_within_24h_whatsapp_more_recent(self):
        """Both platforms available, WhatsApp more recent (< 24h) should select WhatsApp."""
        telegram_chat = self._create_chat_config(ChatConfigDB.ChatType.telegram, "telegram_chat_123")
        whatsapp_chat = self._create_chat_config(ChatConfigDB.ChatType.whatsapp, "whatsapp_user_123")

        telegram_message = self._create_message(
            telegram_chat.chat_id,
            self.mock_user.id,
            datetime.now(UTC) - timedelta(hours = 10),
        )
        whatsapp_message = self._create_message(
            whatsapp_chat.chat_id,
            self.mock_user.id,
            datetime.now(UTC) - timedelta(hours = 2),
        )

        def get_chat(external_id, chat_type):
            if chat_type == ChatConfigDB.ChatType.telegram:
                return telegram_chat
            elif chat_type == ChatConfigDB.ChatType.whatsapp:
                return whatsapp_chat
            return None

        self.mock_di.chat_config_crud.get_by_external_identifiers = Mock(side_effect = get_chat)

        def get_messages(chat_id, limit):
            if chat_id == telegram_chat.chat_id:
                return [telegram_message]
            elif chat_id == whatsapp_chat.chat_id:
                return [whatsapp_message]
            return []

        self.mock_di.chat_message_crud.get_latest_chat_messages = Mock(side_effect = get_messages)

        service = SysAnnouncementsService("Test", None, self.mock_configured_tool, self.mock_di)
        resolved_chat = service._SysAnnouncementsService__resolved_chat

        self.assertEqual(resolved_chat.chat_type, ChatConfigDB.ChatType.whatsapp)

    def test_both_within_24h_telegram_more_recent(self):
        """Both platforms available, Telegram more recent, WhatsApp < 24h should select Telegram."""
        telegram_chat = self._create_chat_config(ChatConfigDB.ChatType.telegram, "telegram_chat_123")
        whatsapp_chat = self._create_chat_config(ChatConfigDB.ChatType.whatsapp, "whatsapp_user_123")

        telegram_message = self._create_message(
            telegram_chat.chat_id,
            self.mock_user.id,
            datetime.now(UTC) - timedelta(hours = 2),
        )
        whatsapp_message = self._create_message(
            whatsapp_chat.chat_id,
            self.mock_user.id,
            datetime.now(UTC) - timedelta(hours = 10),
        )

        def get_chat(external_id, chat_type):
            if chat_type == ChatConfigDB.ChatType.telegram:
                return telegram_chat
            elif chat_type == ChatConfigDB.ChatType.whatsapp:
                return whatsapp_chat
            return None

        self.mock_di.chat_config_crud.get_by_external_identifiers = Mock(side_effect = get_chat)

        def get_messages(chat_id, limit):
            if chat_id == telegram_chat.chat_id:
                return [telegram_message]
            elif chat_id == whatsapp_chat.chat_id:
                return [whatsapp_message]
            return []

        self.mock_di.chat_message_crud.get_latest_chat_messages = Mock(side_effect = get_messages)

        service = SysAnnouncementsService("Test", None, self.mock_configured_tool, self.mock_di)
        resolved_chat = service._SysAnnouncementsService__resolved_chat

        self.assertEqual(resolved_chat.chat_type, ChatConfigDB.ChatType.telegram)

    def test_whatsapp_outside_24h_telegram_available(self):
        """WhatsApp > 24h, Telegram available should select Telegram."""
        telegram_chat = self._create_chat_config(ChatConfigDB.ChatType.telegram, "telegram_chat_123")
        whatsapp_chat = self._create_chat_config(ChatConfigDB.ChatType.whatsapp, "whatsapp_user_123")

        telegram_message = self._create_message(
            telegram_chat.chat_id,
            self.mock_user.id,
            datetime.now(UTC) - timedelta(hours = 48),
        )
        whatsapp_message = self._create_message(
            whatsapp_chat.chat_id,
            self.mock_user.id,
            datetime.now(UTC) - timedelta(hours = WHATSAPP_MESSAGING_WINDOW_HOURS + 2),
        )

        def get_chat(external_id, chat_type):
            if chat_type == ChatConfigDB.ChatType.telegram:
                return telegram_chat
            elif chat_type == ChatConfigDB.ChatType.whatsapp:
                return whatsapp_chat
            return None

        self.mock_di.chat_config_crud.get_by_external_identifiers = Mock(side_effect = get_chat)

        def get_messages(chat_id, limit):
            if chat_id == telegram_chat.chat_id:
                return [telegram_message]
            elif chat_id == whatsapp_chat.chat_id:
                return [whatsapp_message]
            return []

        self.mock_di.chat_message_crud.get_latest_chat_messages = Mock(side_effect = get_messages)

        service = SysAnnouncementsService("Test", None, self.mock_configured_tool, self.mock_di)
        resolved_chat = service._SysAnnouncementsService__resolved_chat

        self.assertEqual(resolved_chat.chat_type, ChatConfigDB.ChatType.telegram)

    def test_no_platforms_available(self):
        """No platforms configured should raise error."""
        self.mock_di.chat_config_crud.get_by_external_identifiers = Mock(return_value = None)

        with self.assertRaises(ValueError) as context:
            SysAnnouncementsService("Test", None, self.mock_configured_tool, self.mock_di)

        self.assertIn("Cannot resolve target chat", str(context.exception))

    def test_no_messages_in_chat(self):
        """Telegram chat with no messages should still be selected over nothing."""
        telegram_chat = self._create_chat_config(ChatConfigDB.ChatType.telegram, "telegram_chat_123")

        self.mock_di.chat_config_crud.get_by_external_identifiers = Mock(side_effect = lambda external_id, chat_type: (
            telegram_chat if chat_type == ChatConfigDB.ChatType.telegram else None
        ))
        self.mock_di.chat_message_crud.get_latest_chat_messages = Mock(return_value = [])

        service = SysAnnouncementsService("Test", None, self.mock_configured_tool, self.mock_di)
        resolved_chat = service._SysAnnouncementsService__resolved_chat

        self.assertEqual(resolved_chat.chat_type, ChatConfigDB.ChatType.telegram)

    def test_explicit_target_chat_bypasses_selection(self):
        """Passing explicit target_chat should bypass platform selection logic."""
        explicit_chat = self._create_chat_config(ChatConfigDB.ChatType.telegram, "explicit_chat")

        # No need to mock chat_config_crud since platform selection should not be called
        service = SysAnnouncementsService("Test", explicit_chat, self.mock_configured_tool, self.mock_di)
        resolved_chat = service._SysAnnouncementsService__resolved_chat

        self.assertEqual(resolved_chat.external_id, "explicit_chat")
        # Verify get_by_external_identifiers was never called
        self.mock_di.chat_config_crud.get_by_external_identifiers.assert_not_called()
