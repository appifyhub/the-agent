import unittest
from datetime import datetime
from unittest.mock import Mock
from uuid import UUID

from pydantic import SecretStr

from api.authorization_service import AuthorizationService
from db.crud.chat_config import ChatConfigCRUD
from db.crud.user import UserCRUD
from db.model.chat_config import ChatConfigDB
from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.user import User
from di.di import DI
from features.chat.telegram.model.chat_member import ChatMemberAdministrator
from features.chat.telegram.model.user import User as TelegramUser
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK


class AuthorizationServiceTest(unittest.TestCase):
    invoker_user: User
    invoker_telegram_user: TelegramUser
    chat_config: ChatConfig
    mock_user_dao: UserCRUD
    mock_chat_config_dao: ChatConfigCRUD
    mock_telegram_sdk: TelegramBotSDK
    mock_di: DI

    def setUp(self):
        self.invoker_user = User(
            id = UUID(int = 1),
            full_name = "Invoker User",
            telegram_username = "invoker_username",
            telegram_chat_id = "invoker_chat_id",
            telegram_user_id = 1,
            open_ai_key = SecretStr("invoker_api_key"),
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
        self.mock_di = Mock(spec = DI)
        # noinspection PyPropertyAccess
        self.mock_di.telegram_bot_sdk = self.mock_telegram_sdk
        # noinspection PyPropertyAccess
        self.mock_di.user_crud = self.mock_user_dao
        # noinspection PyPropertyAccess
        self.mock_di.chat_config_crud = self.mock_chat_config_dao

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
            can_delete_stories = is_manager,
        )

    def test_validate_chat_success_with_string(self):
        service = AuthorizationService(self.mock_di)
        result = service.validate_chat(self.chat_config.chat_id)
        self.assertEqual(result.chat_id, self.chat_config.chat_id)

    def test_validate_chat_success_with_instance(self):
        service = AuthorizationService(self.mock_di)
        result = service.validate_chat(self.chat_config)
        self.assertEqual(result.chat_id, self.chat_config.chat_id)
        # Should return the same instance that was passed in
        self.assertIs(result, self.chat_config)

    def test_validate_chat_failure_chat_not_found(self):
        self.mock_chat_config_dao.get.return_value = None
        service = AuthorizationService(self.mock_di)
        with self.assertRaises(ValueError) as context:
            service.validate_chat("wrong_chat_id")
        self.assertIn("Chat 'wrong_chat_id' not found", str(context.exception))

    def test_validate_user_success_with_hex_string(self):
        service = AuthorizationService(self.mock_di)
        result = service.validate_user(self.invoker_user.id.hex)
        self.assertEqual(result.id, self.invoker_user.id)

    def test_validate_user_success_with_uuid(self):
        service = AuthorizationService(self.mock_di)
        result = service.validate_user(self.invoker_user.id)
        self.assertEqual(result.id, self.invoker_user.id)

    def test_validate_user_success_with_instance(self):
        service = AuthorizationService(self.mock_di)
        result = service.validate_user(self.invoker_user)
        self.assertEqual(result.id, self.invoker_user.id)
        # Should return the same instance that was passed in
        self.assertIs(result, self.invoker_user)

    def test_validate_user_failure_user_not_found(self):
        # Reset mock to return None for this test
        self.mock_di.user_crud.get.return_value = None
        service = AuthorizationService(self.mock_di)
        with self.assertRaises(ValueError) as context:
            service.validate_user("00000000000000000000000000000000")
        self.assertIn("User '00000000000000000000000000000000' not found", str(context.exception))

    def test_authorize_for_chat_success(self):
        self.mock_chat_config_dao.get_all.return_value = [self.chat_config]
        admin_member = self.create_admin_member(self.invoker_telegram_user, is_manager = True)
        self.mock_telegram_sdk.get_chat_administrators.return_value = [admin_member]

        service = AuthorizationService(self.mock_di)
        result = service.authorize_for_chat(self.invoker_user, self.chat_config.chat_id)
        self.assertEqual(result.chat_id, self.chat_config.chat_id)

    def test_authorize_for_chat_failure_user_not_admin(self):
        self.mock_chat_config_dao.get_all.return_value = [self.chat_config]
        other_admin = self.create_admin_member(
            TelegramUser(id = 999, is_bot = False, first_name = "Other"),
            is_manager = True,
        )
        self.mock_telegram_sdk.get_chat_administrators.return_value = [other_admin]

        service = AuthorizationService(self.mock_di)
        with self.assertRaises(ValueError) as context:
            service.authorize_for_chat(self.invoker_user, self.chat_config.chat_id)
        self.assertIn("is not admin in", str(context.exception))

    def test_authorize_for_user_success(self):
        service = AuthorizationService(self.mock_di)
        result = service.authorize_for_user(self.invoker_user, self.invoker_user.id.hex)
        self.assertEqual(result.id, self.invoker_user.id)

    def test_authorize_for_user_failure_different_user(self):
        other_user = User(
            id = UUID(int = 2),
            full_name = "Other User",
            telegram_username = "other_username",
            telegram_chat_id = "other_chat_id",
            telegram_user_id = 2,
            open_ai_key = SecretStr("other_api_key"),
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.mock_user_dao.get.return_value = other_user

        service = AuthorizationService(self.mock_di)
        with self.assertRaises(ValueError) as context:
            service.authorize_for_user(self.invoker_user, other_user.id.hex)
        self.assertIn("is not the allowed user", str(context.exception))

    def test_get_authorized_chats_success_user_is_admin(self):
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
            is_manager = True,
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

        self.mock_telegram_sdk.get_chat_administrators.side_effect = mock_get_admins

        service = AuthorizationService(self.mock_di)
        admin_chats = service.get_authorized_chats(self.invoker_user)

        self.assertEqual(len(admin_chats), 2)
        admin_chat_ids = [chat.chat_id for chat in admin_chats]
        self.assertIn(chat_config_1.chat_id, admin_chat_ids)
        self.assertIn(chat_config_3.chat_id, admin_chat_ids)
        self.assertNotIn(chat_config_2.chat_id, admin_chat_ids)

    def test_get_authorized_chats_success_user_administers_multiple_chats(self):
        chat_config1 = ChatConfig(
            chat_id = "chat_id_1", title = "Admin Chat 1", language_iso_code = "en", reply_chance_percent = 50,
            is_private = False, release_notifications = ChatConfigDB.ReleaseNotifications.all,
        )
        chat_config2 = ChatConfig(
            chat_id = "chat_id_2", title = "Non-Admin Chat", language_iso_code = "es", reply_chance_percent = 70,
            is_private = False, release_notifications = ChatConfigDB.ReleaseNotifications.all,
        )
        chat_config3 = ChatConfig(
            chat_id = "chat_id_3", title = "Admin Chat 2", language_iso_code = "fr", reply_chance_percent = 60,
            is_private = False, release_notifications = ChatConfigDB.ReleaseNotifications.all,
        )
        all_chat_configs = [chat_config1, chat_config2, chat_config3]
        self.mock_chat_config_dao.get_all.return_value = all_chat_configs

        admin_member = self.create_admin_member(self.invoker_telegram_user, is_manager = True)
        other_admin_member = self.create_admin_member(
            TelegramUser(id = 999, is_bot = False, first_name = "OtherAdmin"),
            is_manager = True,
        )

        def mock_get_admins(chat_id_param):
            if chat_id_param == chat_config1.chat_id:
                return [admin_member, other_admin_member]
            elif chat_id_param == chat_config2.chat_id:
                return [other_admin_member]
            elif chat_id_param == chat_config3.chat_id:
                return [other_admin_member, admin_member]
            return []

        self.mock_telegram_sdk.get_chat_administrators.side_effect = mock_get_admins

        service = AuthorizationService(self.mock_di)
        admin_chats = service.get_authorized_chats(self.invoker_user)

        self.assertEqual(len(admin_chats), 2)
        admin_chat_ids = [chat.chat_id for chat in admin_chats]
        self.assertIn(chat_config1.chat_id, admin_chat_ids)
        self.assertIn(chat_config3.chat_id, admin_chat_ids)
        self.assertNotIn(chat_config2.chat_id, admin_chat_ids)

    def test_get_authorized_chats_user_no_telegram_id(self):
        user_without_telegram_id = User(
            id = UUID(int = 1),
            full_name = "User Without Telegram ID",
            telegram_username = "user_no_telegram",
            telegram_chat_id = None,
            telegram_user_id = None,
            open_ai_key = SecretStr("api_key"),
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )

        service = AuthorizationService(self.mock_di)
        admin_chats = service.get_authorized_chats(user_without_telegram_id)

        self.assertEqual(len(admin_chats), 0)

    def test_get_authorized_chats_sorting_order(self):
        private_chat = ChatConfig(
            chat_id = self.invoker_user.telegram_chat_id or "invoker_chat_id",
            title = "Private Chat",
            is_private = True,
            language_iso_code = "en",
            reply_chance_percent = 100,
        )
        group_chat_z = ChatConfig(
            chat_id = "group_z_id",
            title = "Z Group",
            is_private = False,
            language_iso_code = "en",
            reply_chance_percent = 50,
        )
        group_chat_a = ChatConfig(
            chat_id = "group_a_id",
            title = "A Group",
            is_private = False,
            language_iso_code = "en",
            reply_chance_percent = 50,
        )
        group_chat_no_title = ChatConfig(
            chat_id = "group_no_title_id",
            title = None,
            is_private = False,
            language_iso_code = "en",
            reply_chance_percent = 50,
        )

        all_chats_db = [
            ChatConfigDB(**chat.model_dump()) for chat in
            [group_chat_z, private_chat, group_chat_no_title, group_chat_a]
        ]
        self.mock_chat_config_dao.get_all.return_value = all_chats_db

        admin_member = self.create_admin_member(self.invoker_telegram_user, is_manager = True)
        self.mock_telegram_sdk.get_chat_administrators.return_value = [admin_member]

        service = AuthorizationService(self.mock_di)
        admin_chats = service.get_authorized_chats(self.invoker_user)

        expected_order = [
            private_chat.chat_id,
            group_chat_no_title.chat_id,
            group_chat_a.chat_id,
            group_chat_z.chat_id,
        ]

        actual_order = [chat.chat_id for chat in admin_chats]
        self.assertEqual(actual_order, expected_order)

    def test_authorize_for_chat_success_with_instance(self):
        # Test that authorize_for_chat works with ChatConfig instance
        self.mock_di.chat_config_crud.get_all.return_value = [self.chat_config]
        admin_member = self.create_admin_member(self.invoker_telegram_user, is_manager = True)
        self.mock_di.telegram_bot_sdk.get_chat_administrators.return_value = [admin_member]

        service = AuthorizationService(self.mock_di)
        result = service.authorize_for_chat(self.invoker_user, self.chat_config)
        self.assertEqual(result.chat_id, self.chat_config.chat_id)

    def test_authorize_for_user_success_with_uuid(self):
        service = AuthorizationService(self.mock_di)
        result = service.authorize_for_user(self.invoker_user, self.invoker_user.id)
        self.assertEqual(result.id, self.invoker_user.id)

    def test_authorize_for_user_success_with_instance(self):
        service = AuthorizationService(self.mock_di)
        result = service.authorize_for_user(self.invoker_user, self.invoker_user)
        self.assertEqual(result.id, self.invoker_user.id)
        # Should return the same instance that was passed in
        self.assertIs(result, self.invoker_user)
