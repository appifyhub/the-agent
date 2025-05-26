import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import UUID

from db.crud.chat_config import ChatConfigCRUD
from db.crud.user import UserCRUD
from db.model.chat_config import ChatConfigDB
from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.user import User, UserSave
from features.chat.chat_config_manager import ChatConfigManager
from features.chat.settings_manager import SettingsManager
from features.chat.telegram.model.chat_member import ChatMemberAdministrator, ChatMemberMember
from features.chat.telegram.model.user import User as TelegramUser
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from util.functions import mask_secret


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
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
        )
        self.chat_member = self.create_admin_member(self.invoker_telegram_user, is_manager = False)
        self.mock_user_dao = Mock(spec = UserCRUD)
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao = Mock(spec = ChatConfigCRUD)
        self.mock_chat_config_dao.get.return_value = self.chat_config
        self.mock_telegram_sdk = Mock(spec = TelegramBotSDK)
        self.mock_telegram_sdk.get_chat_member.return_value = self.chat_member

    @staticmethod
    def create_admin_member(telegram_user, is_manager = True):
        """Helper method to create a ChatMemberAdministrator with all required fields"""
        return ChatMemberAdministrator(
            status = "administrator",
            user = telegram_user,
            can_be_edited = False,
            is_anonymous = False,
            can_manage_chat = is_manager,
            can_delete_messages = is_manager,
            can_manage_video_chats = is_manager,
            can_restrict_members = is_manager,
            can_promote_members = is_manager,
            can_change_info = is_manager,
            can_invite_users = is_manager,
            can_post_stories = is_manager,
            can_edit_stories = is_manager,
            can_delete_stories = is_manager
        )

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
        self.assertIn("not admin", str(context.exception))

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
        self.assertIn("not admin", str(context.exception))

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

    @patch.object(SettingsManager, "_SettingsManager__validate", lambda x, y, z, w: None)
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

    @patch.object(SettingsManager, "_SettingsManager__validate", lambda x, y, z, w: None)
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
        self.assertEqual(settings["open_ai_key"], mask_secret(self.invoker_user.open_ai_key))
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.mock_user_dao.get.call_count, 2)

    @patch.object(ChatConfigManager, "change_chat_language", return_value = (ChatConfigManager.Result.success, ""))
    @patch.object(ChatConfigManager, "change_chat_reply_chance", return_value = (ChatConfigManager.Result.success, ""))
    @patch.object(
        ChatConfigManager,
        "change_chat_release_notifications",
        return_value = (ChatConfigManager.Result.success, "")
    )
    def test_save_chat_settings_success(
        self,
        mock_change_chat_release_notifications,
        mock_change_chat_reply_chance,
        mock_change_chat_language,
    ):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        manager.save_chat_settings(
            chat_id = self.chat_config.chat_id,
            language_name = "Spanish",
            language_iso_code = "es",
            reply_chance_percent = 50,
            release_notifications = "all",
        )

        mock_change_chat_language.assert_called_once_with(
            chat_id = self.chat_config.chat_id,
            language_name = "Spanish",
            language_iso_code = "es",
        )
        mock_change_chat_reply_chance.assert_called_once_with(
            chat_id = self.chat_config.chat_id,
            reply_chance_percent = 50,
        )
        mock_change_chat_release_notifications.assert_called_once_with(
            chat_id = self.chat_config.chat_id,
            raw_selection = "all",
        )

    def test_save_user_settings_success(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        # Configure mock to return a proper UserDB instance
        self.mock_user_dao.save.return_value = UserDB(
            id = self.invoker_user.id,
            full_name = self.invoker_user.full_name,
            telegram_username = self.invoker_user.telegram_username,
            telegram_chat_id = self.invoker_user.telegram_chat_id,
            telegram_user_id = self.invoker_user.telegram_user_id,
            open_ai_key = "new_open_ai_key",
            group = self.invoker_user.group,
            created_at = self.invoker_user.created_at,
        )

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        manager.save_user_settings(
            user_id_hex = self.invoker_user.id.hex,
            open_ai_key = "new_open_ai_key",
        )

        self.invoker_user.open_ai_key = "new_open_ai_key"
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.save.assert_called_once_with(UserSave(**self.invoker_user.model_dump()))

    # noinspection PyUnusedLocal
    @patch.object(ChatConfigManager, "change_chat_language", return_value = (ChatConfigManager.Result.failure, "Error"))
    def test_save_chat_settings_failure_language(self, mock_change_chat_language):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        with self.assertRaises(ValueError) as context:
            manager.save_chat_settings(
                chat_id = self.chat_config.chat_id,
                language_name = "Spanish",
                language_iso_code = "es",
                reply_chance_percent = 50,
                release_notifications = "all",
            )
        self.assertIn("Error", str(context.exception))

    @patch.object(ChatConfigManager, "change_chat_language", return_value = (ChatConfigManager.Result.success, ""))
    @patch.object(
        ChatConfigManager,
        "change_chat_reply_chance",
        return_value = (ChatConfigManager.Result.failure, "Error")
    )
    def test_save_chat_settings_failure_reply_chance(self, mock_change_chat_reply_chance, mock_change_chat_language):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config
        # Configure mock to return the same chat config structure
        mock_change_chat_language.return_value = (ChatConfigManager.Result.success, "")
        mock_change_chat_reply_chance.return_value = (ChatConfigManager.Result.failure, "Error")

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        with self.assertRaises(ValueError) as context:
            manager.save_chat_settings(
                chat_id = self.chat_config.chat_id,
                language_name = "Spanish",
                language_iso_code = "es",
                reply_chance_percent = 50,
                release_notifications = "all",
            )
        self.assertIn("Error", str(context.exception))

    @patch.object(ChatConfigManager, "change_chat_language", return_value = (ChatConfigManager.Result.success, ""))
    @patch.object(ChatConfigManager, "change_chat_reply_chance", return_value = (ChatConfigManager.Result.success, ""))
    @patch.object(
        ChatConfigManager,
        "change_chat_release_notifications",
        return_value = (ChatConfigManager.Result.failure, "Invalid notifications level")
    )
    def test_save_chat_settings_failure_release_notifications(
        self,
        mock_change_chat_release_notifications,
        mock_change_chat_reply_chance,
        mock_change_chat_language,
    ):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        with self.assertRaises(ValueError) as context:
            manager.save_chat_settings(
                chat_id = self.chat_config.chat_id,
                language_name = "Spanish",
                language_iso_code = "es",
                reply_chance_percent = 50,
                release_notifications = "invalid_level"
            )
        self.assertIn("Invalid notifications level", str(context.exception))

        mock_change_chat_language.assert_called_once()
        mock_change_chat_reply_chance.assert_called_once()
        mock_change_chat_release_notifications.assert_called_once_with(
            chat_id = self.chat_config.chat_id,
            raw_selection = "invalid_level",
        )

    def test_save_chat_settings_missing_release_notifications(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        with self.assertRaises(TypeError):
            # noinspection PyArgumentList
            manager.save_chat_settings(
                chat_id = self.chat_config.chat_id,
                language_name = "Spanish",
                language_iso_code = "es",
                reply_chance_percent = 50,
                # Missing release_notifications parameter
            )

    def test_get_admin_chats_success_user_is_admin(self):
        chat_config_1 = ChatConfig(
            chat_id = "chat_A_id",
            title = "Chat Alpha",
            is_private = False,
            language_iso_code = "en",
            reply_chance_percent = 50,
        )
        chat_config_2 = ChatConfig(
            chat_id = "chat_B_id",
            title = "Chat Bravo",
            is_private = False,
            language_iso_code = "en",
            reply_chance_percent = 50,
        )
        chat_config_3 = ChatConfig(
            chat_id = "chat_C_id",
            title = "Chat Charlie",
            is_private = False,
            language_iso_code = "en",
            reply_chance_percent = 50,
        )

        chat_config_1_db = ChatConfigDB(**chat_config_1.model_dump())
        chat_config_2_db = ChatConfigDB(**chat_config_2.model_dump())
        chat_config_3_db = ChatConfigDB(**chat_config_3.model_dump())

        admin_member_invoker = self.create_admin_member(self.invoker_telegram_user, is_manager = True)
        admin_member_other = self.create_admin_member(
            TelegramUser(id = 67890, is_bot = False, first_name = "Other", username = "other_admin"),
            is_manager = True
        )

        self.mock_chat_config_dao.get_all.return_value = [chat_config_1_db, chat_config_2_db, chat_config_3_db]

        def mock_get_admins(chat_id_param):
            if chat_id_param == chat_config_1.chat_id:
                return [admin_member_invoker, admin_member_other]
            if chat_id_param == chat_config_2.chat_id:
                return [admin_member_other]
            if chat_id_param == chat_config_3.chat_id:
                return [admin_member_invoker]
            return []

        self.mock_telegram_sdk.get_chat_administrators = Mock(side_effect = mock_get_admins)

        # noinspection PyUnresolvedReferences
        self.mock_user_dao.reset_mock()
        self.mock_user_dao.get.return_value = self.invoker_user

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        admin_chats = manager.get_admin_chats_for_user(self.invoker_user)

        self.assertEqual(len(admin_chats), 2)
        self.assertEqual(admin_chats[0].title, "Chat Alpha")
        self.assertEqual(admin_chats[1].title, "Chat Charlie")

        # noinspection PyUnresolvedReferences
        self.assertEqual(self.mock_user_dao.get.call_count, 1)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.get.assert_any_call(UUID(hex = self.invoker_user.id.hex))
        # noinspection PyUnresolvedReferences
        self.mock_chat_config_dao.get_all.assert_called_once()
        self.mock_telegram_sdk.get_chat_administrators.assert_any_call(chat_config_1.chat_id)
        self.mock_telegram_sdk.get_chat_administrators.assert_any_call(chat_config_2.chat_id)
        self.mock_telegram_sdk.get_chat_administrators.assert_any_call(chat_config_3.chat_id)
        self.assertEqual(self.mock_telegram_sdk.get_chat_administrators.call_count, 3)

    def test_get_admin_chats_success_user_is_not_admin_in_any(self):
        chat_config_1 = ChatConfig(
            chat_id = "chat_A_id",
            title = "Chat Alpha",
            is_private = False,
            language_iso_code = "en",
            reply_chance_percent = 50,
        )
        chat_config_2 = ChatConfig(
            chat_id = "chat_B_id",
            title = "Chat Bravo",
            is_private = False,
            language_iso_code = "es",
            reply_chance_percent = 70,
        )

        chat_config_1_db = ChatConfigDB(**chat_config_1.model_dump())
        chat_config_2_db = ChatConfigDB(**chat_config_2.model_dump())

        admin_member_other = self.create_admin_member(
            TelegramUser(id = 67890, is_bot = False, first_name = "Other", username = "other_admin"),
            is_manager = True
        )

        self.mock_chat_config_dao.get_all.return_value = [chat_config_1_db, chat_config_2_db]
        self.mock_telegram_sdk.get_chat_administrators = Mock(return_value = [admin_member_other])

        # noinspection PyUnresolvedReferences
        self.mock_user_dao.reset_mock()
        self.mock_user_dao.get.return_value = self.invoker_user

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        admin_chats = manager.get_admin_chats_for_user(self.invoker_user)
        self.assertEqual(len(admin_chats), 0)

        # noinspection PyUnresolvedReferences
        self.assertEqual(self.mock_user_dao.get.call_count, 1)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.get.assert_any_call(UUID(hex = self.invoker_user.id.hex))
        # noinspection PyUnresolvedReferences
        self.mock_chat_config_dao.get_all.assert_called_once()
        self.mock_telegram_sdk.get_chat_administrators.assert_any_call(chat_config_1.chat_id)
        self.mock_telegram_sdk.get_chat_administrators.assert_any_call(chat_config_2.chat_id)
        self.assertEqual(self.mock_telegram_sdk.get_chat_administrators.call_count, 2)

    def test_get_admin_chats_sdk_returns_none_for_one_chat(self):
        chat_config_1 = ChatConfig(
            chat_id = "chat_A_id",
            title = "Chat Alpha",
            is_private = False,
            language_iso_code = "en",
            reply_chance_percent = 50,
        )
        chat_config_2 = ChatConfig(
            chat_id = "chat_B_id",
            title = "Chat Bravo",
            is_private = False,
            language_iso_code = "en",
            reply_chance_percent = 50,
        )

        chat_config_1_db = ChatConfigDB(**chat_config_1.model_dump())
        chat_config_2_db = ChatConfigDB(**chat_config_2.model_dump())

        admin_member_invoker = self.create_admin_member(self.invoker_telegram_user, is_manager = True)

        self.mock_chat_config_dao.get_all.return_value = [chat_config_1_db, chat_config_2_db]

        def mock_get_admins(chat_id_param):
            if chat_id_param == chat_config_1.chat_id:
                return [admin_member_invoker]
            if chat_id_param == chat_config_2.chat_id:
                return None
            return []

        self.mock_telegram_sdk.get_chat_administrators = Mock(side_effect = mock_get_admins)

        # noinspection PyUnresolvedReferences
        self.mock_user_dao.reset_mock()
        self.mock_user_dao.get.return_value = self.invoker_user

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        admin_chats = manager.get_admin_chats_for_user(self.invoker_user)
        self.assertEqual(len(admin_chats), 1)
        self.assertEqual(admin_chats[0].chat_id, chat_config_1.chat_id)

        # noinspection PyUnresolvedReferences
        self.assertEqual(self.mock_user_dao.get.call_count, 1)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.get.assert_any_call(UUID(hex = self.invoker_user.id.hex))
        # noinspection PyUnresolvedReferences
        self.mock_chat_config_dao.get_all.assert_called_once()

    def test_get_admin_chats_no_telegram_id_for_user(self):
        user_no_telegram_id_db = self.invoker_user.model_copy()
        user_no_telegram_id_db.telegram_user_id = None

        user_dao_for_test = Mock(spec = UserCRUD)
        user_dao_for_test.get.return_value = user_no_telegram_id_db

        chat_config_dao_for_test = Mock(spec = ChatConfigCRUD)
        chat_config_dao_for_test.get.return_value = self.chat_config
        chat_config_dao_for_test.get_all.return_value = []

        telegram_sdk_for_test = Mock(spec = TelegramBotSDK)
        telegram_sdk_for_test.get_chat_member.return_value = self.chat_member

        manager_for_test = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = telegram_sdk_for_test,
            user_dao = user_dao_for_test,
            chat_config_dao = chat_config_dao_for_test,
        )

        admin_chats = manager_for_test.get_admin_chats_for_user(self.invoker_user)
        self.assertEqual(len(admin_chats), 0)
        self.assertEqual(user_dao_for_test.get.call_count, 1)

    def test_get_admin_chats_no_chat_configs_in_db(self):
        self.mock_chat_config_dao.get_all.return_value = []

        # noinspection PyUnresolvedReferences
        self.mock_user_dao.reset_mock()
        self.mock_user_dao.get.return_value = self.invoker_user

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        admin_chats = manager.get_admin_chats_for_user(self.invoker_user)
        self.assertEqual(len(admin_chats), 0)

        # noinspection PyUnresolvedReferences
        self.assertEqual(self.mock_user_dao.get.call_count, 1)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.get.assert_any_call(UUID(hex = self.invoker_user.id.hex))
        # noinspection PyUnresolvedReferences
        self.mock_chat_config_dao.get_all.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_telegram_sdk.get_chat_administrators.assert_not_called()

    def test_get_admin_chats_success_user_administers_multiple_chats(self):

        # 1. Setup: Create multiple chat configurations
        chat_config1 = ChatConfig(
            chat_id = "chat_id_1", title = "Admin Chat 1", language_iso_code = "en", reply_chance_percent = 50,
            is_private = False, release_notifications = ChatConfigDB.ReleaseNotifications.all
        )
        chat_config2 = ChatConfig(
            chat_id = "chat_id_2", title = "Non-Admin Chat", language_iso_code = "es", reply_chance_percent = 70,
            is_private = False, release_notifications = ChatConfigDB.ReleaseNotifications.all
        )
        chat_config3 = ChatConfig(
            chat_id = "chat_id_3", title = "Admin Chat 2", language_iso_code = "fr", reply_chance_percent = 60,
            is_private = False, release_notifications = ChatConfigDB.ReleaseNotifications.all
        )
        all_chat_configs = [chat_config1, chat_config2, chat_config3]
        self.mock_chat_config_dao.get_all.return_value = all_chat_configs

        # 2. Setup: Mock telegram_sdk.get_chat_administrators
        # Invoker is admin in chat1 and chat3, but not in chat2
        admin_member = self.create_admin_member(self.invoker_telegram_user, is_manager = True)
        other_admin_member = self.create_admin_member(
            TelegramUser(id = 999, is_bot = False, first_name = "OtherAdmin"),
            is_manager = True
        )

        def mock_get_admins(chat_id_param):
            if chat_id_param == chat_config1.chat_id:
                return [admin_member, other_admin_member]
            elif chat_id_param == chat_config2.chat_id:
                return [other_admin_member]  # Invoker is not an admin here
            elif chat_id_param == chat_config3.chat_id:
                return [other_admin_member, admin_member]
            return []

        self.mock_telegram_sdk.get_chat_administrators.side_effect = mock_get_admins

        # Reset and setup user_dao mock for this specific test's needs if necessary
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.reset_mock()
        self.mock_user_dao.get.return_value = self.invoker_user  # Ensures __init__ and the method call get the user

        # Initialize SettingsManager
        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            # target_chat_id can be any valid chat_id for initialization,
            # as get_admin_chats_for_user doesn't use self.target_chat_id
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )

        # 3. Execute the method
        admin_chats = manager.get_admin_chats_for_user(self.invoker_user)

        # 4. Assertions
        self.assertEqual(len(admin_chats), 2)
        self.assertIn(chat_config1, admin_chats)
        self.assertIn(chat_config3, admin_chats)
        self.assertNotIn(chat_config2, admin_chats)

        # noinspection PyUnresolvedReferences
        # Check mock calls
        self.assertEqual(self.mock_user_dao.get.call_count, 1)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.get.assert_any_call(UUID(hex = self.invoker_user.id.hex))
        # noinspection PyUnresolvedReferences
        self.mock_chat_config_dao.get_all.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.mock_telegram_sdk.get_chat_administrators.call_count, len(all_chat_configs))
        # noinspection PyUnresolvedReferences
        self.mock_telegram_sdk.get_chat_administrators.assert_any_call(chat_config1.chat_id)
        # noinspection PyUnresolvedReferences
        self.mock_telegram_sdk.get_chat_administrators.assert_any_call(chat_config2.chat_id)
        # noinspection PyUnresolvedReferences
        self.mock_telegram_sdk.get_chat_administrators.assert_any_call(chat_config3.chat_id)

    @patch.object(SettingsManager, "get_admin_chats_for_user")
    def test_fetch_admin_chats_success(self, mock_get_admin_chats_for_user):
        self.invoker_user.telegram_chat_id = "invoker_chat_id"  # As in setUp
        own_chat_config = ChatConfig(
            chat_id = str(self.invoker_user.telegram_user_id),
            title = "My Notes",
            language_iso_code = "en",
            reply_chance_percent = 100,
            is_private = True,
            release_notifications = ChatConfigDB.ReleaseNotifications.all
        )
        group_chat_config = ChatConfig(
            chat_id = "group_chat_123",
            title = "Test Group",
            language_iso_code = "es",
            reply_chance_percent = 50,
            is_private = False,
            release_notifications = ChatConfigDB.ReleaseNotifications.all
        )
        no_title_chat_config = ChatConfig(
            chat_id = "no_title_chat_456",
            title = None,
            language_iso_code = "fr",
            reply_chance_percent = 75,
            is_private = False,
            release_notifications = ChatConfigDB.ReleaseNotifications.all
        )
        mock_get_admin_chats_for_user.return_value = [own_chat_config, group_chat_config, no_title_chat_config]

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )
        result = manager.fetch_admin_chats(self.invoker_user.id.hex)

        self.assertEqual(len(result), 3)
        mock_get_admin_chats_for_user.assert_called_once_with(self.invoker_user)
        expected_results = [
            {
                "chat_id": own_chat_config.chat_id,
                "title": own_chat_config.title,
                "is_own": True  # Because chat_id matches invoker's telegram_user_id
            },
            {
                "chat_id": group_chat_config.chat_id,
                "title": group_chat_config.title,
                "is_own": False  # Because chat_id does not match
            },
            {
                "chat_id": no_title_chat_config.chat_id,
                "title": no_title_chat_config.title,  # Should be None
                "is_own": False  # Because chat_id does not match
            }
        ]
        self.assertListEqual(result, expected_results)

    @patch.object(SettingsManager, "get_admin_chats_for_user")
    def test_fetch_admin_chats_no_chats_found(self, mock_get_admin_chats_for_user):
        mock_get_admin_chats_for_user.return_value = []

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )
        result = manager.fetch_admin_chats(self.invoker_user.id.hex)

        self.assertEqual(len(result), 0)
        mock_get_admin_chats_for_user.assert_called_once_with(self.invoker_user)

    @patch.object(SettingsManager, "get_admin_chats_for_user")
    def test_fetch_admin_chats_invoker_no_telegram_id(self, mock_get_admin_chats_for_user):
        original_telegram_user_id = self.invoker_user.telegram_user_id
        self.invoker_user.telegram_user_id = None
        self.mock_user_dao.get.return_value = self.invoker_user
        mock_get_admin_chats_for_user.return_value = []

        manager = SettingsManager(
            invoker_user_id_hex = self.invoker_user.id.hex,
            target_chat_id = self.chat_config.chat_id,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
        )
        result = manager.fetch_admin_chats(self.invoker_user.id.hex)

        self.assertEqual(len(result), 0)
        mock_get_admin_chats_for_user.assert_called_once_with(self.invoker_user)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.get.assert_called_with(UUID(hex = self.invoker_user.id.hex))
        self.invoker_user.telegram_user_id = original_telegram_user_id
        self.mock_user_dao.get.return_value = self.invoker_user
