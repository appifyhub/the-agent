import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import UUID

from api.settings_controller import SettingsController
from db.crud.chat_config import ChatConfigCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.model.chat_config import ChatConfigDB
from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.user import User
from features.chat.chat_config_manager import ChatConfigManager
from features.chat.telegram.model.chat_member import ChatMemberAdministrator
from features.chat.telegram.model.user import User as TelegramUser
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from util.functions import mask_secret


class SettingsControllerTest(unittest.TestCase):
    invoker_user: User
    invoker_telegram_user: TelegramUser
    chat_config: ChatConfig
    mock_user_dao: UserCRUD
    mock_chat_config_dao: ChatConfigCRUD
    mock_sponsorship_dao: SponsorshipCRUD
    mock_telegram_sdk: TelegramBotSDK

    def setUp(self):
        self.invoker_user = User(
            id = UUID(int = 1),
            full_name = "Invoker User",
            telegram_username = "invoker_username",
            telegram_chat_id = "invoker_chat_id",
            telegram_user_id = 1,
            open_ai_key = "invoker_api_key",
            anthropic_key = "test_anthropic_key",
            perplexity_key = "test_perplexity_key",
            replicate_key = "test_replicate_key",
            rapid_api_key = "test_rapid_api_key",
            coinmarketcap_key = "test_coinmarketcap_key",
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
        self.mock_sponsorship_dao = Mock(spec = SponsorshipCRUD)
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []
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
            can_delete_stories = is_manager,
        )

    def test_create_settings_link_success_user_settings(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        # Create private chat config that matches the invoker's chat ID
        private_chat = ChatConfig(
            chat_id = self.invoker_user.telegram_chat_id,
            title = "Private Chat",
            is_private = True,
            language_iso_code = "en",
            reply_chance_percent = 100,
            release_notifications = self.chat_config.release_notifications,
        )
        # Both get() and get_all() should return the same private chat
        self.mock_chat_config_dao.get.return_value = private_chat
        self.mock_chat_config_dao.get_all.return_value = [private_chat]

        manager = SettingsController(
            invoker_user_id_hex = self.invoker_user.id.hex,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
        )
        link = manager.create_settings_link(raw_settings_type = "user")

        self.assertIn("settings?token=", link)
        self.assertIn("/user/", link)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.get.assert_called_once_with(UUID(hex = self.invoker_user.id.hex))

    def test_create_settings_link_success_chat_settings(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config
        # Mock authorization service to allow access
        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_chat.return_value = self.chat_config

            manager = SettingsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
            )
            link = manager.create_settings_link(raw_settings_type = "chat", target_chat_id = self.chat_config.chat_id)

            self.assertIn("settings?token=", link)
            self.assertIn("/chat/", link)

    def test_create_settings_link_failure_invalid_settings_type(self):
        self.mock_user_dao.get.return_value = self.invoker_user

        manager = SettingsController(
            invoker_user_id_hex = self.invoker_user.id.hex,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
        )

        with self.assertRaises(ValueError) as context:
            manager.create_settings_link(raw_settings_type = "invalid_type")
        self.assertIn("Invalid settings type", str(context.exception))

    def test_create_settings_link_failure_chat_settings_no_chat_id(self):
        self.mock_user_dao.get.return_value = self.invoker_user

        manager = SettingsController(
            invoker_user_id_hex = self.invoker_user.id.hex,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
        )

        with self.assertRaises(ValueError) as context:
            manager.create_settings_link(raw_settings_type = "chat")
        self.assertIn("Chat ID must be provided", str(context.exception))

    def test_validate_invoker_not_found(self):
        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.side_effect = ValueError("User not found")

            with self.assertRaises(ValueError) as context:
                SettingsController(
                    invoker_user_id_hex = self.invoker_user.id.hex,
                    telegram_sdk = self.mock_telegram_sdk,
                    user_dao = self.mock_user_dao,
                    chat_config_dao = self.mock_chat_config_dao,
                    sponsorship_dao = self.mock_sponsorship_dao,
                )
            self.assertIn("User not found", str(context.exception))

    def test_fetch_chat_settings_success(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_chat.return_value = self.chat_config

            manager = SettingsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
            )
            settings = manager.fetch_chat_settings(self.chat_config.chat_id)

            self.assertEqual(settings["chat_id"], self.chat_config.chat_id)
            self.assertEqual(settings["is_own"], False)

    def test_fetch_user_settings_success(self):
        self.mock_user_dao.get.return_value = self.invoker_user

        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.invoker_user

            manager = SettingsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
            )
            settings = manager.fetch_user_settings(self.invoker_user.id.hex)

            self.assertEqual(settings["id"], self.invoker_user.id.hex)
            self.assertEqual(settings["open_ai_key"], mask_secret(self.invoker_user.open_ai_key))

    def test_fetch_user_settings_masks_all_token_fields(self):
        self.mock_user_dao.get.return_value = self.invoker_user

        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.invoker_user

            manager = SettingsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
            )
            settings = manager.fetch_user_settings(self.invoker_user.id.hex)

            # Verify all token fields are masked
            self.assertEqual(settings["open_ai_key"], mask_secret(self.invoker_user.open_ai_key))
            self.assertEqual(settings["anthropic_key"], mask_secret(self.invoker_user.anthropic_key))
            self.assertEqual(settings["perplexity_key"], mask_secret(self.invoker_user.perplexity_key))
            self.assertEqual(settings["replicate_key"], mask_secret(self.invoker_user.replicate_key))
            self.assertEqual(settings["rapid_api_key"], mask_secret(self.invoker_user.rapid_api_key))
            self.assertEqual(settings["coinmarketcap_key"], mask_secret(self.invoker_user.coinmarketcap_key))

            # Verify no token is exposed in plain text
            for key, value in settings.items():
                if key.endswith("_key"):
                    self.assertNotIn("test_", str(value), f"Token field '{key}' should be masked but contains test data")
                    self.assertNotIn("api_key", str(value), f"Token field '{key}' should be masked but contains api_key")

    @patch.object(ChatConfigManager, "change_chat_language", return_value = (ChatConfigManager.Result.success, ""))
    @patch.object(
        ChatConfigManager,
        "change_chat_reply_chance",
        return_value = (ChatConfigManager.Result.success, ""),
    )
    @patch.object(
        ChatConfigManager,
        "change_chat_release_notifications",
        return_value = (ChatConfigManager.Result.success, ""),
    )
    def test_save_chat_settings_success(
        self,
        mock_change_chat_release_notifications,
        mock_change_chat_reply_chance,
        mock_change_chat_language,
    ):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_chat.return_value = self.chat_config

            manager = SettingsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
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

    def test_save_user_settings_with_all_tokens(self):
        # Create a proper UserDB mock for the save return value
        saved_user_db = UserDB(
            id = self.invoker_user.id,
            full_name = self.invoker_user.full_name,
            telegram_username = self.invoker_user.telegram_username,
            telegram_chat_id = self.invoker_user.telegram_chat_id,
            telegram_user_id = self.invoker_user.telegram_user_id,
            open_ai_key = "new_openai_key",
            anthropic_key = "new_anthropic_key",
            perplexity_key = "new_perplexity_key",
            replicate_key = "new_replicate_key",
            rapid_api_key = "new_rapid_api_key",
            coinmarketcap_key = "new_coinmarketcap_key",
            group = self.invoker_user.group,
            created_at = self.invoker_user.created_at,
        )
        self.mock_user_dao.save.return_value = saved_user_db

        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.invoker_user

            manager = SettingsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
            )

            result = manager.save_user_settings(
                user_id_hex = self.invoker_user.id.hex,
                open_ai_key = "new_openai_key",
                anthropic_key = "new_anthropic_key",
                perplexity_key = "new_perplexity_key",
                replicate_key = "new_replicate_key",
                rapid_api_key = "new_rapid_api_key",
                coinmarketcap_key = "new_coinmarketcap_key",
            )

            # Verify the save was called with the updated data
            self.mock_user_dao.save.assert_called_once()
            saved_user_data = self.mock_user_dao.save.call_args[0][0]

            self.assertEqual(saved_user_data.open_ai_key, "new_openai_key")
            self.assertEqual(saved_user_data.anthropic_key, "new_anthropic_key")
            self.assertEqual(saved_user_data.perplexity_key, "new_perplexity_key")
            self.assertEqual(saved_user_data.replicate_key, "new_replicate_key")
            self.assertEqual(saved_user_data.rapid_api_key, "new_rapid_api_key")
            self.assertEqual(saved_user_data.coinmarketcap_key, "new_coinmarketcap_key")
            self.assertIsNone(result)  # Method returns None

    # noinspection PyUnusedLocal
    @patch.object(ChatConfigManager, "change_chat_language", return_value = (ChatConfigManager.Result.failure, "Error"))
    def test_save_chat_settings_failure_language(self, mock_change_chat_language):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_chat.return_value = self.chat_config

            manager = SettingsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
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
        return_value = (ChatConfigManager.Result.failure, "Error"),
    )
    def test_save_chat_settings_failure_reply_chance(self, mock_change_chat_reply_chance, mock_change_chat_language):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config
        # Configure mock to return the same chat config structure
        mock_change_chat_language.return_value = (ChatConfigManager.Result.success, "")
        mock_change_chat_reply_chance.return_value = (ChatConfigManager.Result.failure, "Error")

        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_chat.return_value = self.chat_config

            manager = SettingsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
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
        return_value = (ChatConfigManager.Result.failure, "Invalid notifications level"),
    )
    def test_save_chat_settings_failure_release_notifications(
        self,
        mock_change_chat_release_notifications,
        mock_change_chat_reply_chance,
        mock_change_chat_language,
    ):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_chat.return_value = self.chat_config

            manager = SettingsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
            )

            with self.assertRaises(ValueError) as context:
                manager.save_chat_settings(
                    chat_id = self.chat_config.chat_id,
                    language_name = "Spanish",
                    language_iso_code = "es",
                    reply_chance_percent = 50,
                    release_notifications = "invalid_level",
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

        manager = SettingsController(
            invoker_user_id_hex = self.invoker_user.id.hex,
            telegram_sdk = self.mock_telegram_sdk,
            user_dao = self.mock_user_dao,
            chat_config_dao = self.mock_chat_config_dao,
            sponsorship_dao = self.mock_sponsorship_dao,
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

    def test_fetch_admin_chats_success(self):
        self.invoker_user.telegram_chat_id = "invoker_chat_id"  # As in setUp
        own_chat_config = ChatConfig(
            chat_id = str(self.invoker_user.telegram_chat_id),
            title = "My Notes",
            language_iso_code = "en",
            reply_chance_percent = 100,
            is_private = True,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
        )
        group_chat_config = ChatConfig(
            chat_id = "group_chat_123",
            title = "Test Group",
            language_iso_code = "es",
            reply_chance_percent = 50,
            is_private = False,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
        )
        no_title_chat_config = ChatConfig(
            chat_id = "no_title_chat_456",
            title = None,
            language_iso_code = "fr",
            reply_chance_percent = 75,
            is_private = False,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
        )

        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.invoker_user
            mock_auth_service.get_authorized_chats.return_value = [own_chat_config, group_chat_config,
                                                                   no_title_chat_config]

            manager = SettingsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
            )
            result = manager.fetch_admin_chats(self.invoker_user.id.hex)

            self.assertEqual(len(result), 3)
            mock_auth_service.get_authorized_chats.assert_called_once_with(self.invoker_user)
            expected_results = [
                {
                    "chat_id": own_chat_config.chat_id,
                    "title": own_chat_config.title,
                    "is_own": True,  # Because chat_id matches invoker's telegram_user_id
                },
                {
                    "chat_id": group_chat_config.chat_id,
                    "title": group_chat_config.title,
                    "is_own": False,  # Because chat_id does not match
                },
                {
                    "chat_id": no_title_chat_config.chat_id,
                    "title": no_title_chat_config.title,  # Should be None
                    "is_own": False,  # Because chat_id does not match
                },
            ]
            self.assertListEqual(result, expected_results)

    def test_fetch_admin_chats_no_chats_found(self):
        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_user.return_value = self.invoker_user
            mock_auth_service.get_authorized_chats.return_value = []

            manager = SettingsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
            )
            result = manager.fetch_admin_chats(self.invoker_user.id.hex)

            self.assertEqual(len(result), 0)
            mock_auth_service.get_authorized_chats.assert_called_once_with(self.invoker_user)
