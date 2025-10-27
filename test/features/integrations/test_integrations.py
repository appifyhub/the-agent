from datetime import date
from unittest import TestCase
from unittest.mock import Mock
from uuid import UUID

from pydantic import SecretStr

from db.crud.user import UserCRUD
from db.model.chat_config import ChatConfigDB
from db.model.user import UserDB
from db.schema.user import User, UserSave
from features.integrations.integrations import (
    is_the_agent,
    lookup_user_by_handle,
    resolve_agent_user,
    resolve_any_external_handle,
    resolve_external_handle,
    resolve_external_id,
    resolve_platform_name,
    resolve_private_chat_id,
    resolve_user_link,
    resolve_user_to_save,
)
from util.config import config


class IntegrationsTest(TestCase):

    def test_resolve_agent_user_telegram(self):
        agent = resolve_agent_user(ChatConfigDB.ChatType.telegram)
        self.assertEqual(agent.telegram_username, config.telegram_bot_username)
        self.assertEqual(agent.telegram_user_id, config.telegram_bot_id)
        self.assertEqual(agent.full_name, "The Agent")

    def test_resolve_agent_user_background(self):
        agent = resolve_agent_user(ChatConfigDB.ChatType.background)
        self.assertEqual(agent.full_name, config.background_bot_name)
        self.assertIsNone(agent.telegram_username)
        self.assertIsNone(agent.telegram_user_id)

    def test_resolve_agent_user_github(self):
        agent = resolve_agent_user(ChatConfigDB.ChatType.github)
        self.assertEqual(agent.full_name, "The Agent")
        self.assertEqual(agent.telegram_username, config.telegram_bot_username)
        self.assertEqual(agent.telegram_user_id, config.telegram_bot_id)

    def test_resolve_agent_user_whatsapp(self):
        agent = resolve_agent_user(ChatConfigDB.ChatType.whatsapp)
        self.assertEqual(agent.whatsapp_user_id, config.whatsapp_phone_number_id)
        assert agent.whatsapp_phone_number is not None
        self.assertEqual(agent.whatsapp_phone_number.get_secret_value(), config.whatsapp_bot_phone_number)
        self.assertEqual(agent.full_name, "The Agent")

    def test_resolve_external_id_telegram_success(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_user_id = 123456789,
        )
        result = resolve_external_id(user, ChatConfigDB.ChatType.telegram)
        self.assertEqual(result, "123456789")

    def test_resolve_external_id_telegram_none(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_user_id = None,
        )
        result = resolve_external_id(user, ChatConfigDB.ChatType.telegram)
        self.assertIsNone(result)

    def test_resolve_external_id_unsupported_platform(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_user_id = 123456789,
        )
        result = resolve_external_id(user, ChatConfigDB.ChatType.background)
        self.assertIsNone(result)

    def test_resolve_external_id_whatsapp_success(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            whatsapp_user_id = "15551234567",
        )
        result = resolve_external_id(user, ChatConfigDB.ChatType.whatsapp)
        self.assertEqual(result, "15551234567")

    def test_resolve_external_id_whatsapp_none(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            whatsapp_user_id = None,
        )
        result = resolve_external_id(user, ChatConfigDB.ChatType.whatsapp)
        self.assertIsNone(result)

    def test_resolve_external_handle_telegram_success(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "test_user",
        )
        result = resolve_external_handle(user, ChatConfigDB.ChatType.telegram)
        self.assertEqual(result, "test_user")

    def test_resolve_external_handle_telegram_none(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = None,
        )
        result = resolve_external_handle(user, ChatConfigDB.ChatType.telegram)
        self.assertIsNone(result)

    def test_resolve_external_handle_unsupported_platform(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "test_user",
        )
        result = resolve_external_handle(user, ChatConfigDB.ChatType.github)
        self.assertIsNone(result)

    def test_resolve_external_handle_whatsapp_success(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            whatsapp_phone_number = SecretStr("15551234567"),
        )
        result = resolve_external_handle(user, ChatConfigDB.ChatType.whatsapp)
        self.assertEqual(result, "15551234567")

    def test_resolve_external_handle_whatsapp_none(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            whatsapp_phone_number = None,
        )
        result = resolve_external_handle(user, ChatConfigDB.ChatType.whatsapp)
        self.assertIsNone(result)

    def test_is_the_agent_true(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = config.telegram_bot_username,
            telegram_user_id = config.telegram_bot_id,
        )
        result = is_the_agent(user, ChatConfigDB.ChatType.telegram)
        self.assertTrue(result)

    def test_is_the_agent_false_different_user(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "other_user",
            telegram_user_id = 987654321,
        )
        result = is_the_agent(user, ChatConfigDB.ChatType.telegram)
        self.assertFalse(result)

    def test_is_the_agent_none_user(self):
        result = is_the_agent(None, ChatConfigDB.ChatType.telegram)
        self.assertFalse(result)

    def test_lookup_user_by_handle_telegram_success(self):
        mock_user_crud = Mock(spec = UserCRUD)
        mock_user_db = UserDB(
            id = UUID(int = 1),
            full_name = "Test User",
            telegram_username = "test_user",
            telegram_chat_id = "test_chat",
            telegram_user_id = 123456789,
            group = UserDB.Group.standard,
            created_at = date.today(),
        )
        mock_user_crud.get_by_telegram_username.return_value = mock_user_db

        result = lookup_user_by_handle("test_user", ChatConfigDB.ChatType.telegram, mock_user_crud)

        self.assertEqual(result, mock_user_db)
        mock_user_crud.get_by_telegram_username.assert_called_once_with("test_user")

    def test_lookup_user_by_handle_telegram_not_found(self):
        mock_user_crud = Mock(spec = UserCRUD)
        mock_user_crud.get_by_telegram_username.return_value = None

        result = lookup_user_by_handle("nonexistent_user", ChatConfigDB.ChatType.telegram, mock_user_crud)

        self.assertIsNone(result)
        mock_user_crud.get_by_telegram_username.assert_called_once_with("nonexistent_user")

    def test_lookup_user_by_handle_unsupported_platform(self):
        mock_user_crud = Mock(spec = UserCRUD)

        result = lookup_user_by_handle("test_user", ChatConfigDB.ChatType.background, mock_user_crud)

        self.assertIsNone(result)
        mock_user_crud.get_by_telegram_username.assert_not_called()

    def test_lookup_user_by_handle_whatsapp_success(self):
        mock_user_crud = Mock(spec = UserCRUD)
        mock_user_db = UserDB(
            id = UUID(int = 1),
            full_name = "Test User",
            whatsapp_user_id = "15551234567",
            whatsapp_phone_number = "15551234567",
            group = UserDB.Group.standard,
            created_at = date.today(),
        )
        mock_user_crud.get_by_whatsapp_phone_number.return_value = mock_user_db

        result = lookup_user_by_handle("+1 (555) 123-4567", ChatConfigDB.ChatType.whatsapp, mock_user_crud)

        self.assertEqual(result, mock_user_db)
        mock_user_crud.get_by_whatsapp_phone_number.assert_called_once_with("15551234567")

    def test_lookup_user_by_handle_whatsapp_not_found(self):
        mock_user_crud = Mock(spec = UserCRUD)
        mock_user_crud.get_by_whatsapp_phone_number.return_value = None

        result = lookup_user_by_handle("+1 (555) 999-9999", ChatConfigDB.ChatType.whatsapp, mock_user_crud)

        self.assertIsNone(result)
        mock_user_crud.get_by_whatsapp_phone_number.assert_called_once_with("15559999999")

    def test_resolve_user_to_save_telegram_success(self):
        result = resolve_user_to_save("test_user", ChatConfigDB.ChatType.telegram)

        assert result is not None
        self.assertIsInstance(result, UserSave)
        self.assertEqual(result.telegram_username, "test_user")
        self.assertIsNone(result.id)
        self.assertIsNone(result.full_name)
        self.assertIsNone(result.telegram_chat_id)
        self.assertIsNone(result.telegram_user_id)
        self.assertEqual(result.group, UserDB.Group.standard)

    def test_resolve_user_to_save_unsupported_platform(self):
        result = resolve_user_to_save("test_user", ChatConfigDB.ChatType.background)

        self.assertIsNone(result)

    def test_resolve_user_to_save_whatsapp_success(self):
        result = resolve_user_to_save("+1 (555) 123-4567", ChatConfigDB.ChatType.whatsapp)

        assert result is not None
        self.assertIsInstance(result, UserSave)
        self.assertEqual(result.whatsapp_user_id, "15551234567")
        assert result.whatsapp_phone_number is not None
        self.assertEqual(result.whatsapp_phone_number.get_secret_value(), "15551234567")
        self.assertIsNone(result.id)
        self.assertIsNone(result.full_name)
        self.assertEqual(result.group, UserDB.Group.standard)

    def test_resolve_any_external_handle_telegram_success(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "test_user",
        )
        handle, chat_type = resolve_any_external_handle(user)
        self.assertEqual(handle, "test_user")
        self.assertEqual(chat_type, ChatConfigDB.ChatType.telegram)

    def test_resolve_any_external_handle_telegram_with_whitespace(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "  test_user  ",
        )
        handle, chat_type = resolve_any_external_handle(user)
        self.assertEqual(handle, "test_user")  # Should be stripped
        self.assertEqual(chat_type, ChatConfigDB.ChatType.telegram)

    def test_resolve_any_external_handle_telegram_empty_string(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "",
        )
        handle, chat_type = resolve_any_external_handle(user)
        self.assertIsNone(handle)
        self.assertIsNone(chat_type)

    def test_resolve_any_external_handle_telegram_whitespace_only(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "   ",
        )
        handle, chat_type = resolve_any_external_handle(user)
        self.assertIsNone(handle)
        self.assertIsNone(chat_type)

    def test_resolve_any_external_handle_no_handles(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = None,
        )
        handle, chat_type = resolve_any_external_handle(user)
        self.assertIsNone(handle)
        self.assertIsNone(chat_type)

    def test_resolve_any_external_handle_prioritizes_first_available(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "telegram_user",
        )
        handle, chat_type = resolve_any_external_handle(user)
        self.assertEqual(handle, "telegram_user")
        self.assertEqual(chat_type, ChatConfigDB.ChatType.telegram)

    def test_resolve_any_external_handle_whatsapp_success(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            whatsapp_phone_number = SecretStr("15551234567"),
        )
        handle, chat_type = resolve_any_external_handle(user)
        self.assertEqual(handle, "15551234567")
        self.assertEqual(chat_type, ChatConfigDB.ChatType.whatsapp)

    def test_resolve_any_external_handle_whatsapp_with_whitespace(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            whatsapp_phone_number = SecretStr("  15551234567  "),
        )
        handle, chat_type = resolve_any_external_handle(user)
        self.assertEqual(handle, "15551234567")  # Should be stripped
        self.assertEqual(chat_type, ChatConfigDB.ChatType.whatsapp)

    def test_resolve_any_external_handle_whatsapp_empty_string(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            whatsapp_phone_number = SecretStr(""),
        )
        handle, chat_type = resolve_any_external_handle(user)
        self.assertIsNone(handle)
        self.assertIsNone(chat_type)

    def test_resolve_any_external_handle_telegram_and_whatsapp_prioritizes_telegram(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "telegram_user",
            whatsapp_phone_number = SecretStr("15551234567"),
        )
        handle, chat_type = resolve_any_external_handle(user)
        self.assertEqual(handle, "telegram_user")  # Telegram should be prioritized
        self.assertEqual(chat_type, ChatConfigDB.ChatType.telegram)

    def test_resolve_user_link_telegram_success(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "test_user",
        )
        result = resolve_user_link(user, ChatConfigDB.ChatType.telegram)
        self.assertEqual(result, "[@test_user](https://t.me/test_user)")

    def test_resolve_user_link_telegram_with_at_prefix(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "@test_user",
        )
        result = resolve_user_link(user, ChatConfigDB.ChatType.telegram)
        self.assertEqual(result, "[@test_user](https://t.me/test_user)")

    def test_resolve_user_link_telegram_with_plus_prefix(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "+test_user",
        )
        result = resolve_user_link(user, ChatConfigDB.ChatType.telegram)
        self.assertEqual(result, "[@test_user](https://t.me/test_user)")

    def test_resolve_user_link_telegram_with_slash_prefix(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "/test_user",
        )
        result = resolve_user_link(user, ChatConfigDB.ChatType.telegram)
        self.assertEqual(result, "[@test_user](https://t.me/test_user)")

    def test_resolve_user_link_telegram_empty_username(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "",
        )
        result = resolve_user_link(user, ChatConfigDB.ChatType.telegram)
        self.assertIsNone(result)

    def test_resolve_user_link_telegram_whitespace_only(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "   ",
        )
        result = resolve_user_link(user, ChatConfigDB.ChatType.telegram)
        self.assertIsNone(result)

    def test_resolve_user_link_telegram_none_username(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = None,
        )
        result = resolve_user_link(user, ChatConfigDB.ChatType.telegram)
        self.assertIsNone(result)

    def test_resolve_user_link_github_no_handle(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "test_user",  # GitHub doesn't use telegram_username
        )
        result = resolve_user_link(user, ChatConfigDB.ChatType.github)
        self.assertIsNone(result)  # GitHub handle resolution not implemented yet

    def test_resolve_user_link_background_platform(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_username = "test_user",
        )
        result = resolve_user_link(user, ChatConfigDB.ChatType.background)
        self.assertIsNone(result)

    def test_resolve_user_link_whatsapp_success(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            whatsapp_phone_number = SecretStr("15551234567"),
        )
        result = resolve_user_link(user, ChatConfigDB.ChatType.whatsapp)
        self.assertEqual(result, "[15551234567](https://wa.me/15551234567)")

    def test_resolve_user_link_whatsapp_with_plus_prefix(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            whatsapp_phone_number = SecretStr("+15551234567"),
        )
        result = resolve_user_link(user, ChatConfigDB.ChatType.whatsapp)
        self.assertEqual(result, "[15551234567](https://wa.me/15551234567)")

    def test_resolve_user_link_whatsapp_formatted_phone(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            whatsapp_phone_number = SecretStr("+1 (555) 123-4567"),
        )
        result = resolve_user_link(user, ChatConfigDB.ChatType.whatsapp)
        self.assertEqual(result, "[15551234567](https://wa.me/15551234567)")

    def test_resolve_user_link_whatsapp_empty_phone_number(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            whatsapp_phone_number = SecretStr(""),
        )
        result = resolve_user_link(user, ChatConfigDB.ChatType.whatsapp)
        self.assertIsNone(result)

    def test_resolve_user_link_whatsapp_none_phone_number(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            whatsapp_phone_number = None,
        )
        result = resolve_user_link(user, ChatConfigDB.ChatType.whatsapp)
        self.assertIsNone(result)

    def test_resolve_platform_name_telegram(self):
        result = resolve_platform_name(ChatConfigDB.ChatType.telegram)
        self.assertEqual(result, "Telegram")

    def test_resolve_platform_name_background(self):
        result = resolve_platform_name(ChatConfigDB.ChatType.background)
        self.assertEqual(result, "Pulse")

    def test_resolve_platform_name_github(self):
        result = resolve_platform_name(ChatConfigDB.ChatType.github)
        self.assertEqual(result, "GitHub")

    def test_resolve_platform_name_whatsapp(self):
        result = resolve_platform_name(ChatConfigDB.ChatType.whatsapp)
        self.assertEqual(result, "WhatsApp")

    def test_resolve_private_chat_id_telegram_success(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_chat_id = "123456789",
        )
        result = resolve_private_chat_id(user, ChatConfigDB.ChatType.telegram)
        self.assertEqual(result, "123456789")

    def test_resolve_private_chat_id_telegram_none(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_chat_id = None,
        )
        result = resolve_private_chat_id(user, ChatConfigDB.ChatType.telegram)
        self.assertIsNone(result)

    def test_resolve_private_chat_id_background_platform(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_chat_id = "123456789",
        )
        result = resolve_private_chat_id(user, ChatConfigDB.ChatType.background)
        self.assertIsNone(result)

    def test_resolve_private_chat_id_github_platform(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            telegram_chat_id = "123456789",
        )
        result = resolve_private_chat_id(user, ChatConfigDB.ChatType.github)
        self.assertIsNone(result)

    def test_resolve_private_chat_id_whatsapp_success(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            whatsapp_user_id = "15551234567",
        )
        result = resolve_private_chat_id(user, ChatConfigDB.ChatType.whatsapp)
        self.assertEqual(result, "15551234567")

    def test_resolve_private_chat_id_whatsapp_none(self):
        user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            whatsapp_user_id = None,
        )
        result = resolve_private_chat_id(user, ChatConfigDB.ChatType.whatsapp)
        self.assertIsNone(result)
