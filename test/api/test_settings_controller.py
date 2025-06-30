import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

from pydantic import SecretStr

from api.models.chat_settings_payload import ChatSettingsPayload
from api.models.user_settings_payload import UserSettingsPayload
from api.settings_controller import SettingsController
from db.crud.chat_config import ChatConfigCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.model.chat_config import ChatConfigDB
from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.user import User
from features.chat.telegram.model.chat_member import ChatMemberAdministrator
from features.chat.telegram.model.user import User as TelegramUser
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.external_tools.external_tool import ExternalTool, ExternalToolProvider, ToolType
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
        self.invoker_telegram_user = TelegramUser(
            id = 123456789,
            is_bot = False,
            first_name = "Test",
            last_name = "User",
            username = "testuser",
            language_code = "en",
        )
        self.invoker_user = User(
            id = UUID("12345678-1234-5678-1234-567812345678"),
            full_name = "Test User",
            telegram_username = "testuser",
            telegram_chat_id = "123456789",
            telegram_user_id = 123456789,
            open_ai_key = "test_openai_key",
            anthropic_key = "test_anthropic_key",
            perplexity_key = "test_perplexity_key",
            replicate_key = "test_replicate_key",
            rapid_api_key = "test_rapid_api_key",
            coinmarketcap_key = "test_coinmarketcap_key",
            group = UserDB.Group.developer,
            created_at = datetime.now().date(),
        )
        self.chat_config = ChatConfig(
            chat_id = "test_chat_123",
            title = "Test Chat",
            language_iso_code = "en",
            reply_chance_percent = 75,
            is_private = False,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
        )

        # Create mocks
        self.mock_user_dao = MagicMock(spec = UserCRUD)
        self.mock_chat_config_dao = MagicMock(spec = ChatConfigCRUD)
        self.mock_sponsorship_dao = MagicMock(spec = SponsorshipCRUD)
        self.mock_telegram_sdk = MagicMock(spec = TelegramBotSDK)

        # Configure common mock returns
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config
        self.mock_sponsorship_dao.get_all_by_receiver.return_value = []

    @staticmethod
    def create_admin_member(telegram_user, is_manager = True):
        return ChatMemberAdministrator(
            user = telegram_user,
            status = "administrator",
            can_be_edited = True,
            can_manage_chat = is_manager,
            can_change_info = True,
            can_delete_messages = True,
            can_invite_users = True,
            can_restrict_members = True,
            can_pin_messages = True,
            can_promote_members = False,
            is_anonymous = False,
            can_manage_video_chats = True,
            can_post_stories = False,
            can_edit_stories = False,
            can_delete_stories = False,
        )

    def test_create_settings_link_success_user_settings(self):
        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user

            manager = SettingsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
            )
            link = manager.create_settings_link()

            self.assertIn("user", link)
            self.assertIn(self.invoker_user.id.hex, link)
            self.assertIn("token=", link)

    def test_create_settings_link_success_chat_settings(self):
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

            self.assertIn("chat", link)
            self.assertIn(self.chat_config.chat_id, link)
            self.assertIn("token=", link)

    def test_create_settings_link_failure_invalid_settings_type(self):
        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user

            manager = SettingsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
            )

            with self.assertRaises(ValueError) as context:
                manager.create_settings_link(raw_settings_type = "invalid")
            self.assertIn("Invalid settings type", str(context.exception))

    def test_create_settings_link_failure_chat_settings_no_chat_id(self):
        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user

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
                    self.assertNotIn(
                        "test_",
                        str(value),
                        f"Token field '{key}' should be masked but contains test data",
                    )
                    self.assertNotIn(
                        "api_key",
                        str(value),
                        f"Token field '{key}' should be masked but contains api_key",
                    )

    def test_save_chat_settings_success(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        # Mock the save method to return a proper ChatConfigDB object
        saved_chat_config_db = ChatConfigDB(
            chat_id = self.chat_config.chat_id,
            title = self.chat_config.title,
            language_iso_code = "es",  # Updated value
            language_name = "Spanish",  # Updated value
            reply_chance_percent = 50,  # Updated value
            is_private = self.chat_config.is_private,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,  # Updated value
        )
        self.mock_chat_config_dao.save.return_value = saved_chat_config_db

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

            payload = ChatSettingsPayload(
                language_name = "Spanish",
                language_iso_code = "es",
                reply_chance_percent = 50,
                release_notifications = "all",
            )
            manager.save_chat_settings(self.chat_config.chat_id, payload)

            # Verify the save was called with updated data
            # noinspection PyUnresolvedReferences
            self.mock_chat_config_dao.save.assert_called_once()

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

            payload = UserSettingsPayload(
                open_ai_key = "new_openai_key",
                anthropic_key = "new_anthropic_key",
                perplexity_key = "new_perplexity_key",
                replicate_key = "new_replicate_key",
                rapid_api_key = "new_rapid_api_key",
                coinmarketcap_key = "new_coinmarketcap_key",
            )
            result = manager.save_user_settings(self.invoker_user.id.hex, payload)

            # Verify the save was called with the updated data
            # noinspection PyUnresolvedReferences
            self.mock_user_dao.save.assert_called_once()
            # noinspection PyUnresolvedReferences
            saved_user_data = self.mock_user_dao.save.call_args[0][0]

            self.assertEqual(saved_user_data.open_ai_key, "new_openai_key")
            self.assertEqual(saved_user_data.anthropic_key, "new_anthropic_key")
            self.assertEqual(saved_user_data.perplexity_key, "new_perplexity_key")
            self.assertEqual(saved_user_data.replicate_key, "new_replicate_key")
            self.assertEqual(saved_user_data.rapid_api_key, "new_rapid_api_key")
            self.assertEqual(saved_user_data.coinmarketcap_key, "new_coinmarketcap_key")
            self.assertIsNone(result)  # Method returns None

    def test_save_chat_settings_failure_language_mismatch(self):
        """Test that providing empty language fields fails"""
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
                payload = ChatSettingsPayload(
                    language_name = "",  # Empty string after trimming
                    language_iso_code = "es",
                    reply_chance_percent = 50,
                    release_notifications = "all",
                )
                manager.save_chat_settings(self.chat_config.chat_id, payload)
            self.assertIn("Both language_name and language_iso_code must be non-empty", str(context.exception))

    def test_save_chat_settings_failure_reply_chance_private_chat(self):
        """Test that private chats can't have reply chance changed"""
        self.mock_user_dao.get.return_value = self.invoker_user
        private_chat_config = ChatConfig(
            chat_id = "private_chat_123",
            title = "Private Chat",
            language_iso_code = "en",
            reply_chance_percent = 100,
            is_private = True,  # This is the key difference
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
        )
        self.mock_chat_config_dao.get.return_value = private_chat_config

        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            mock_auth_service = MockAuthService.return_value
            mock_auth_service.validate_user.return_value = self.invoker_user
            mock_auth_service.authorize_for_chat.return_value = private_chat_config

            manager = SettingsController(
                invoker_user_id_hex = self.invoker_user.id.hex,
                telegram_sdk = self.mock_telegram_sdk,
                user_dao = self.mock_user_dao,
                chat_config_dao = self.mock_chat_config_dao,
                sponsorship_dao = self.mock_sponsorship_dao,
            )

            with self.assertRaises(ValueError) as context:
                payload = ChatSettingsPayload(
                    language_name = "English",
                    language_iso_code = "en",
                    reply_chance_percent = 50,  # Trying to change private chat reply chance
                    release_notifications = "all",
                )
                manager.save_chat_settings(private_chat_config.chat_id, payload)
            self.assertIn("Chat is private, reply chance cannot be changed", str(context.exception))

    def test_save_chat_settings_failure_invalid_release_notifications(self):
        """Test that invalid release notification values are rejected"""
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
                payload = ChatSettingsPayload(
                    language_name = "English",
                    language_iso_code = "en",
                    reply_chance_percent = 50,
                    release_notifications = "invalid_level",
                )
                manager.save_chat_settings(self.chat_config.chat_id, payload)
            self.assertIn("Invalid release notifications setting value 'invalid_level'", str(context.exception))

    def test_save_chat_settings_success_all_fields(self):
        """Test successful save with all fields provided"""
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        # Mock the save method to return a proper ChatConfigDB object
        saved_chat_config_db = ChatConfigDB(
            chat_id = self.chat_config.chat_id,
            title = self.chat_config.title,
            language_iso_code = "es",  # Updated value
            language_name = "Spanish",  # Updated value
            reply_chance_percent = 75,  # Updated value
            is_private = self.chat_config.is_private,
            release_notifications = ChatConfigDB.ReleaseNotifications.major,  # Updated value
        )
        self.mock_chat_config_dao.save.return_value = saved_chat_config_db

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

            # Test successful update with all fields
            payload = ChatSettingsPayload(
                language_name = "Spanish",
                language_iso_code = "es",
                reply_chance_percent = 75,
                release_notifications = "major",
            )
            manager.save_chat_settings(self.chat_config.chat_id, payload)

            # Verify the save was called
            # noinspection PyUnresolvedReferences
            self.mock_chat_config_dao.save.assert_called_once()

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

    @patch("api.settings_controller.AccessTokenResolver")
    def test_fetch_external_tools_success_mixed_configuration(self, mock_resolver_class):
        """Test fetch_external_tools with mixed configuration (some configured, some not)"""
        # Create mock tools and providers
        mock_tool_1 = ExternalTool(
            id = "configured-tool",
            name = "Configured Tool",
            provider = ExternalToolProvider(
                id = "configured-provider",
                name = "Configured Provider",
                token_management_url = "https://example.com",
                token_format = "test-format",
                tools = ["configured-tool"],
            ),
            types = [ToolType.llm],
        )
        mock_tool_2 = ExternalTool(
            id = "unconfigured-tool",
            name = "Unconfigured Tool",
            provider = ExternalToolProvider(
                id = "unconfigured-provider",
                name = "Unconfigured Provider",
                token_management_url = "https://example.com",
                token_format = "test-format",
                tools = ["unconfigured-tool"],
            ),
            types = [ToolType.vision],
        )
        mock_provider_1 = ExternalToolProvider(
            id = "configured-provider",
            name = "Configured Provider",
            token_management_url = "https://example.com",
            token_format = "test-format",
            tools = ["configured-tool"],
        )
        mock_provider_2 = ExternalToolProvider(
            id = "unconfigured-provider",
            name = "Unconfigured Provider",
            token_management_url = "https://example.com",
            token_format = "test-format",
            tools = ["unconfigured-tool"],
        )

        # Mock resolver to return token only for the first tool/provider
        mock_resolver = mock_resolver_class.return_value

        def mock_get_token_for_tool(tool):
            return SecretStr("test-token") if tool.id == "configured-tool" else None

        def mock_get_token(provider):
            return SecretStr("test-token") if provider.id == "configured-provider" else None

        mock_resolver.get_access_token_for_tool.side_effect = mock_get_token_for_tool
        mock_resolver.require_access_token_for_tool.side_effect = mock_get_token_for_tool
        mock_resolver.get_access_token.side_effect = mock_get_token
        mock_resolver.require_access_token.side_effect = mock_get_token

        self.mock_user_dao.get.return_value = self.invoker_user

        with patch("api.settings_controller.AuthorizationService") as MockAuthService:
            with patch("api.settings_controller.ALL_EXTERNAL_TOOLS", [mock_tool_1, mock_tool_2]):
                with patch("api.settings_controller.ALL_PROVIDERS", [mock_provider_1, mock_provider_2]):
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

                    result = manager.fetch_external_tools(self.invoker_user.id.hex)

        # Verify result structure
        self.assertIn("tools", result)
        self.assertIn("providers", result)
        self.assertEqual(len(result["tools"]), 2)
        self.assertEqual(len(result["providers"]), 2)

        # Verify mixed configuration
        configured_tools = [tool for tool in result["tools"] if tool["is_configured"]]
        unconfigured_tools = [tool for tool in result["tools"] if not tool["is_configured"]]
        self.assertEqual(len(configured_tools), 1)
        self.assertEqual(len(unconfigured_tools), 1)

        configured_providers = [provider for provider in result["providers"] if provider["is_configured"]]
        unconfigured_providers = [provider for provider in result["providers"] if not provider["is_configured"]]
        self.assertEqual(len(configured_providers), 1)
        self.assertEqual(len(unconfigured_providers), 1)
