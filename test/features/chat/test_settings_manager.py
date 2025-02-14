import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import UUID

from db.crud.chat_config import ChatConfigCRUD
from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.user import User
from features.chat.settings_manager import SettingsManager
from features.chat.telegram.model.chat_member import ChatMemberAdministrator, ChatMemberMember
from features.chat.telegram.model.user import User as TelegramUser
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK


class SettingsManagerTest(unittest.TestCase):
    invoker_user: User
    invoker_telegram_user: TelegramUser
    chat_config: ChatConfig
    mock_user_dao: UserCRUD
    mock_chat_config_dao: ChatConfigCRUD
    mock_telegram_sdk: TelegramBotSDK

    def setUp(self):
        self.invoker_user = User(
            id = UUID(int = 1),
            full_name = "Invoker User",
            telegram_username = "invoker_username",
            telegram_chat_id = "invoker_chat_id",
            telegram_user_id = 1,
            open_ai_key = "invoker_api_key",
            group = UserDB.Group.developer,
            created_at = datetime.now().date(),
        )
        self.invoker_telegram_user = TelegramUser(
            id = 1,
            is_bot = False,
            first_name = "Invoker",
            last_name = "User",
            username = "invoker_username",
            language_code = "en",
        )
        self.chat_config = ChatConfig(
            chat_id = "test_chat_id",
            language_iso_code = "en",
            language_name = "English",
            reply_chance_percent = 100,
            title = "Test Chat",
            is_private = False,
        )
        self.chat_member = ChatMemberAdministrator(
            status = "administrator", can_be_edited = False, is_anonymous = False, can_manage_chat = False,
            can_delete_messages = False, can_manage_video_chats = False, can_restrict_members = False,
            can_promote_members = False, can_change_info = False, can_invite_users = False, can_post_stories = False,
            can_edit_stories = False, can_delete_stories = False, user = self.invoker_telegram_user,
        )
        self.mock_user_dao = Mock(spec = UserCRUD)
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao = Mock(spec = ChatConfigCRUD)
        self.mock_chat_config_dao.get.return_value = self.chat_config
        self.mock_telegram_sdk = Mock(spec = TelegramBotSDK)
        self.mock_telegram_sdk.get_chat_member.return_value = self.chat_member

    def test_create_settings_link_success(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
            settings_type = "chat_settings",
        )
        link = manager.create_settings_link()

        self.assertIn("settings?token=", link)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.get.assert_called_once_with(UUID(hex = self.invoker_user.id.hex))
        # noinspection PyUnresolvedReferences
        self.mock_chat_config_dao.get.assert_called_once_with(self.chat_config.chat_id)

    def test_create_settings_link_failure_invalid_settings_type(self):
        with self.assertRaises(ValueError) as context:
            SettingsManager(
                invoker_user_id_hex = self.invoker_user.id.hex,
                target_chat_id = self.chat_config.chat_id,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                settings_type = "invalid_type",
            )
        self.assertIn("Invalid settings type", str(context.exception))

    def test_send_settings_link_success(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
            settings_type = "chat_settings",
        )
        link = manager.create_settings_link()
        manager.send_settings_link(link)

        # noinspection PyUnresolvedReferences
        self.mock_telegram_sdk.send_button_link.assert_called_once_with(
            chat_id = self.invoker_user.telegram_user_id,
            link_url = link,
            url_type = "chat_settings",
        )

    def test_validate_invoker_not_found(self):
        self.mock_user_dao.get.return_value = None

        with self.assertRaises(ValueError) as context:
            SettingsManager(
                invoker_user_id_hex = self.invoker_user.id.hex,
                target_chat_id = self.chat_config.chat_id,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                settings_type = None,
            )
        self.assertIn("Invoker", str(context.exception))

    def test_validate_chat_not_found(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = None

        with self.assertRaises(ValueError) as context:
            SettingsManager(
                invoker_user_id_hex = self.invoker_user.id.hex,
                target_chat_id = self.chat_config.chat_id,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                settings_type = None,
            )
        self.assertIn("Chat", str(context.exception))

    def test_validate_not_admin(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config
        self.mock_telegram_sdk.get_chat_member.return_value = Mock(status = "member")

        with self.assertRaises(ValueError) as context:
            SettingsManager(
                invoker_user_id_hex = self.invoker_user.id.hex,
                target_chat_id = self.chat_config.chat_id,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                settings_type = None,
            )
        self.assertIn("not an admin", str(context.exception))

    def test_validate_invoker_in_own_private_chat(self):
        self.chat_config.is_private = True
        self.chat_config.chat_id = str(self.invoker_user.telegram_user_id)
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        try:
            SettingsManager(
                invoker_user_id_hex = self.invoker_user.id.hex,
                target_chat_id = self.chat_config.chat_id,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                settings_type = None,
            )
        except ValueError:
            self.fail("SettingsManager raised ValueError unexpectedly!")

    def test_validate_invoker_in_another_private_chat(self):
        self.chat_config.is_private = True
        self.chat_config.chat_id = "another_private_chat_id"
        self.chat_member = ChatMemberMember(status = "member", user = self.invoker_telegram_user)
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config
        self.mock_telegram_sdk.get_chat_member.return_value = self.chat_member

        with self.assertRaises(ValueError) as context:
            SettingsManager(
                invoker_user_id_hex = self.invoker_user.id.hex,
                target_chat_id = self.chat_config.chat_id,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                settings_type = None,
            )
        self.assertIn("not an admin", str(context.exception))

    def test_authorize_for_chat_different_chat(self):
        self.mock_chat_config_dao.get.return_value = self.chat_config  # for __init__

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        different_chat = ChatConfig(
            chat_id = "different_chat_id",
            language_iso_code = self.chat_config.language_iso_code,
            language_name = self.chat_config.language_name,
            reply_chance_percent = self.chat_config.reply_chance_percent,
            title = self.chat_config.title,
            is_private = self.chat_config.is_private,
        )
        self.mock_chat_config_dao.get.return_value = different_chat

        with self.assertRaises(ValueError) as context:
            manager.authorize_for_chat("different_chat_id")
        self.assertIn("Target chat", str(context.exception))

    def test_authorize_for_chat_not_found(self):
        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        self.mock_chat_config_dao.get.return_value = None
        with self.assertRaises(ValueError) as context:
            manager.authorize_for_chat("wrong_chat_id")
        self.assertIn("Chat 'wrong_chat_id' not found", str(context.exception))

    def test_authorize_for_user_different_user(self):
        self.mock_user_dao.get.return_value = self.invoker_user  # for __init__

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        different_user = User(
            id = UUID(int = 2),
            full_name = self.invoker_user.full_name,
            telegram_username = self.invoker_user.telegram_username,
            telegram_chat_id = self.invoker_user.telegram_chat_id,
            telegram_user_id = self.invoker_user.telegram_user_id,
            open_ai_key = self.invoker_user.open_ai_key,
            group = self.invoker_user.group,
            created_at = self.invoker_user.created_at,
        )
        self.mock_user_dao.get.return_value = different_user

        with self.assertRaises(ValueError) as context:
            manager.authorize_for_user(different_user.id.hex)
        self.assertIn("Target user", str(context.exception))

    def test_authorize_for_user_not_found(self):
        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        self.mock_user_dao.get.return_value = None
        test_uuid = UUID(int = 999).hex
        with self.assertRaises(ValueError) as context:
            manager.authorize_for_user(test_uuid)
        self.assertIn(f"User '{test_uuid}' not found", str(context.exception))

    @patch.object(SettingsManager, '_SettingsManager__validate', lambda x, y, z, w: None)
    def test_fetch_chat_settings_failure_chat_not_found(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = None

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        with self.assertRaises(ValueError) as context:
            manager.fetch_chat_settings("wrong_chat_id")
        self.assertIn("Chat 'wrong_chat_id' not found", str(context.exception))

    @patch.object(SettingsManager, '_SettingsManager__validate', lambda x, y, z, w: None)
    def test_fetch_user_settings_failure_user_not_found(self):
        self.mock_user_dao.get.return_value = None
        self.mock_chat_config_dao.get.return_value = self.chat_config

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        with self.assertRaises(ValueError) as context:
            manager.fetch_user_settings("00000000000000000000000000000000")
        self.assertIn("User '00000000000000000000000000000000' not found", str(context.exception))

    def test_fetch_chat_settings_success(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )
        settings = manager.fetch_chat_settings(self.chat_config.chat_id)

        self.assertEqual(settings["chat_id"], self.chat_config.chat_id)
        self.assertEqual(settings["is_own"], False)
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.mock_chat_config_dao.get.call_count, 2)

    def test_fetch_user_settings_success(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )
        settings = manager.fetch_user_settings(self.invoker_user.id.hex)

        self.assertEqual(settings["id"], self.invoker_user.id.hex)
        self.assertEqual(settings["open_ai_key"], "in***********ey")
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.mock_user_dao.get.call_count, 2)
