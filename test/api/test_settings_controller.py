import unittest
from datetime import datetime
from unittest.mock import MagicMock, PropertyMock, patch
from uuid import UUID

from pydantic import SecretStr

from api.authorization_service import AuthorizationService
from api.model.chat_settings_payload import ChatSettingsPayload
from api.model.user_settings_payload import UserSettingsPayload
from api.settings_controller import SettingsController
from db.crud.chat_config import ChatConfigCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.model.chat_config import ChatConfigDB
from db.model.user import UserDB
from db.model.user import UserDB as UserDBModel
from db.schema.chat_config import ChatConfig
from db.schema.user import User
from di.di import DI
from features.chat.telegram.model.chat_member import ChatMemberAdministrator
from features.chat.telegram.model.user import User as TelegramUser
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.external_tools.access_token_resolver import AccessTokenResolver
from features.external_tools.external_tool import ExternalTool, ExternalToolProvider, ToolType
from util.functions import mask_secret


class SettingsControllerTest(unittest.TestCase):

    invoker_user: User
    invoker_telegram_user: TelegramUser
    chat_config: ChatConfig
    mock_di: DI
    mock_user_dao: UserCRUD
    mock_chat_config_dao: ChatConfigCRUD
    mock_sponsorship_dao: SponsorshipCRUD
    mock_telegram_sdk: TelegramBotSDK
    mock_authorization_service: AuthorizationService
    mock_access_token_resolver: AccessTokenResolver

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
            open_ai_key = SecretStr("test_openai_key"),
            anthropic_key = SecretStr("test_anthropic_key"),
            perplexity_key = SecretStr("test_perplexity_key"),
            replicate_key = SecretStr("test_replicate_key"),
            rapid_api_key = SecretStr("test_rapid_api_key"),
            coinmarketcap_key = SecretStr("test_coinmarketcap_key"),
            tool_choice_chat = "gpt-4o",
            tool_choice_reasoning = "claude-3-5-sonnet-latest",
            tool_choice_vision = "gpt-4o",
            tool_choice_images_gen = "dall-e-3",
            tool_choice_search = "perplexity-search",
            group = UserDB.Group.developer,
            created_at = datetime.now().date(),
        )
        self.chat_config = ChatConfig(
            chat_id = UUID(int = 1),
            external_id = "test_chat_123",
            title = "Test Chat",
            language_iso_code = "en",
            reply_chance_percent = 75,
            is_private = False,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
            chat_type = ChatConfigDB.ChatType.telegram,
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

        # Create mock DI container
        self.mock_di = MagicMock(spec = DI)
        # noinspection PyPropertyAccess
        type(self.mock_di).invoker = PropertyMock(return_value = self.invoker_user)
        # noinspection PyPropertyAccess
        type(self.mock_di).invoker_chat = PropertyMock(return_value = self.chat_config)
        # noinspection PyPropertyAccess
        type(self.mock_di).invoker_chat_type = PropertyMock(return_value = ChatConfigDB.ChatType.telegram)
        # noinspection PyPropertyAccess
        self.mock_di.user_crud = self.mock_user_dao
        # noinspection PyPropertyAccess
        self.mock_di.chat_config_crud = self.mock_chat_config_dao
        # noinspection PyPropertyAccess
        self.mock_di.sponsorship_crud = self.mock_sponsorship_dao
        # noinspection PyPropertyAccess
        self.mock_di.telegram_bot_sdk = self.mock_telegram_sdk

        # Mock authorization service
        self.mock_authorization_service = MagicMock()
        self.mock_authorization_service.authorize_for_chat.return_value = self.chat_config
        self.mock_authorization_service.authorize_for_user.return_value = self.invoker_user
        self.mock_authorization_service.get_authorized_chats.return_value = []
        # noinspection PyPropertyAccess
        self.mock_di.authorization_service = self.mock_authorization_service

        # Mock access token resolver
        self.mock_access_token_resolver = MagicMock()
        self.mock_access_token_resolver.get_access_token_for_tool.return_value = None
        self.mock_access_token_resolver.get_access_token.return_value = None
        self.mock_di.access_token_resolver.return_value = self.mock_access_token_resolver

        # Mock URL shortener to return same URL
        def mock_url_shortener(long_url, **kwargs):
            mock_shortener = MagicMock()
            mock_shortener.execute.return_value = long_url
            return mock_shortener
        self.mock_di.url_shortener = MagicMock(side_effect = mock_url_shortener)

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
        controller = SettingsController(self.mock_di)
        link = controller.create_settings_link()

        self.assertIn("user", link)
        self.assertIn(self.invoker_user.id.hex, link)
        self.assertIn("token=", link)

    def test_create_settings_link_success_chat_settings(self):
        controller = SettingsController(self.mock_di)
        # noinspection PyPropertyAccess
        self.mock_di.invoker_chat_id = self.chat_config.chat_id.hex
        # noinspection PyPropertyAccess
        self.mock_di.invoker_chat = self.chat_config
        link = controller.create_settings_link("chat")

        self.assertIn("chat", link)
        self.assertIn(self.chat_config.chat_id.hex, link)
        self.assertIn("token=", link)

    def test_create_settings_link_failure_invalid_settings_type(self):
        controller = SettingsController(self.mock_di)

        with self.assertRaises(ValueError) as context:
            controller.create_settings_link("invalid_type")

        self.assertIn("Invalid settings type", str(context.exception))

    def test_create_settings_link_failure_chat_settings_no_chat_id(self):
        controller = SettingsController(self.mock_di)

        # noinspection PyPropertyAccess
        self.mock_di.invoker_chat_id = None
        # noinspection PyPropertyAccess
        self.mock_di.invoker_chat = None
        # Force auth failure to reflect missing chat context
        self.mock_authorization_service.authorize_for_chat.side_effect = ValueError(
            "badly formed hexadecimal UUID string",
        )
        with self.assertRaises(ValueError) as context:
            controller.create_settings_link("chat")
        self.assertIn("badly formed hexadecimal UUID string", str(context.exception))

    def test_fetch_chat_settings_success(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        controller = SettingsController(self.mock_di)
        result = controller.fetch_chat_settings("test_chat_123")

        self.assertEqual(result["chat_id"], self.chat_config.chat_id.hex)
        self.assertEqual(result["title"], self.chat_config.title)
        self.assertEqual(result["platform"], self.chat_config.chat_type.value)
        self.assertEqual(result["language_iso_code"], self.chat_config.language_iso_code)
        self.assertEqual(result["reply_chance_percent"], self.chat_config.reply_chance_percent)
        self.assertEqual(result["is_private"], self.chat_config.is_private)
        self.assertEqual(result["release_notifications"], self.chat_config.release_notifications.value)
        self.assertIn("is_own", result)

    def test_fetch_user_settings_success(self):
        self.mock_user_dao.get.return_value = self.invoker_user

        controller = SettingsController(self.mock_di)
        result = controller.fetch_user_settings(self.invoker_user.id.hex)

        self.assertEqual(result["id"], self.invoker_user.id.hex)
        self.assertEqual(result["full_name"], self.invoker_user.full_name)
        self.assertEqual(result["telegram_username"], self.invoker_user.telegram_username)
        self.assertEqual(result["telegram_chat_id"], self.invoker_user.telegram_chat_id)
        self.assertEqual(result["telegram_user_id"], self.invoker_user.telegram_user_id)
        self.assertEqual(result["group"], self.invoker_user.group.value)

    def test_fetch_user_settings_masks_all_token_fields(self):
        self.mock_user_dao.get.return_value = self.invoker_user

        controller = SettingsController(self.mock_di)
        result = controller.fetch_user_settings(self.invoker_user.id.hex)

        self.assertEqual(result["open_ai_key"], mask_secret(self.invoker_user.open_ai_key))
        self.assertEqual(result["anthropic_key"], mask_secret(self.invoker_user.anthropic_key))
        self.assertEqual(result["perplexity_key"], mask_secret(self.invoker_user.perplexity_key))
        self.assertEqual(result["replicate_key"], mask_secret(self.invoker_user.replicate_key))
        self.assertEqual(result["rapid_api_key"], mask_secret(self.invoker_user.rapid_api_key))
        self.assertEqual(result["coinmarketcap_key"], mask_secret(self.invoker_user.coinmarketcap_key))

    def test_save_chat_settings_success(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        # Mock the save method to return a proper ChatConfigDB object
        saved_chat_config_db = ChatConfigDB(
            chat_id = self.chat_config.chat_id,
            external_id = self.chat_config.external_id,
            title = self.chat_config.title,
            language_iso_code = "es",  # Updated value
            language_name = "Spanish",  # Updated value
            reply_chance_percent = 50,  # Updated value
            is_private = self.chat_config.is_private,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,  # Updated value
            chat_type = ChatConfigDB.ChatType.telegram,
        )
        self.mock_chat_config_dao.save.return_value = saved_chat_config_db

        controller = SettingsController(self.mock_di)
        payload = ChatSettingsPayload(
            language_name = "Spanish",
            language_iso_code = "es",
            reply_chance_percent = 50,
            release_notifications = "all",
        )

        # Should not raise any exception
        controller.save_chat_settings("test_chat_123", payload)

        # Verify the save method was called
        # noinspection PyUnresolvedReferences
        self.mock_chat_config_dao.save.assert_called_once()

    @patch("api.settings_controller.SettingsController.fetch_external_tools")
    def test_save_user_settings_with_all_tokens(self, mock_fetch_external_tools):
        # Create a proper UserDB mock for the save return value
        saved_user_db = UserDB(
            id = self.invoker_user.id,
            full_name = self.invoker_user.full_name,
            telegram_username = self.invoker_user.telegram_username,
            telegram_chat_id = self.invoker_user.telegram_chat_id,
            telegram_user_id = self.invoker_user.telegram_user_id,
            open_ai_key = SecretStr("new_openai_key"),
            anthropic_key = SecretStr("new_anthropic_key"),
            perplexity_key = SecretStr("new_perplexity_key"),
            replicate_key = SecretStr("new_replicate_key"),
            rapid_api_key = SecretStr("new_rapid_api_key"),
            coinmarketcap_key = SecretStr("new_coinmarketcap_key"),
            tool_choice_chat = "claude-3-5-sonnet-latest",
            tool_choice_reasoning = "gpt-4o",
            tool_choice_vision = "claude-3-5-sonnet-latest",
            tool_choice_images_gen = "dall-e-2",
            tool_choice_search = "updated-perplexity-search",
            group = self.invoker_user.group,
            created_at = self.invoker_user.created_at,
        )
        self.mock_user_dao.save.return_value = saved_user_db

        # Mock the fetch_external_tools method
        mock_fetch_external_tools.return_value = {
            "tools": [
                {"definition": {"id": "claude-3-5-sonnet-latest"}, "is_configured": True},
                {"definition": {"id": "gpt-4o"}, "is_configured": True},
                {"definition": {"id": "dall-e-2"}, "is_configured": True},
                {"definition": {"id": "updated-perplexity-search"}, "is_configured": True},
            ],
            "providers": [],
        }

        controller = SettingsController(self.mock_di)
        payload = UserSettingsPayload(
            open_ai_key = "new_openai_key",
            anthropic_key = "new_anthropic_key",
            perplexity_key = "new_perplexity_key",
            replicate_key = "new_replicate_key",
            rapid_api_key = "new_rapid_api_key",
            coinmarketcap_key = "new_coinmarketcap_key",
            tool_choice_chat = "claude-3-5-sonnet-latest",
            tool_choice_reasoning = "gpt-4o",
            tool_choice_vision = "claude-3-5-sonnet-latest",
            tool_choice_images_gen = "dall-e-2",
            tool_choice_search = "updated-perplexity-search",
        )

        # Should not raise any exception
        controller.save_user_settings(self.invoker_user.id.hex, payload)

        # Verify the save method was called
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.save.assert_called_once()

    def test_save_user_settings_failure_invalid_tool_choice(self):
        controller = SettingsController(self.mock_di)
        payload = UserSettingsPayload(
            tool_choice_chat = "unconfigured-tool",
        )

        with self.assertRaises(ValueError) as context:
            controller.save_user_settings(self.invoker_user.id.hex, payload)

        self.assertIn("Invalid tool choice", str(context.exception))
        self.assertIn("not configured", str(context.exception))

    def test_save_chat_settings_failure_language_mismatch(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        controller = SettingsController(self.mock_di)
        payload = ChatSettingsPayload(
            language_name = "",  # Empty name should fail
            language_iso_code = "es",
            reply_chance_percent = 50,
            release_notifications = "all",
        )

        with self.assertRaises(ValueError) as context:
            controller.save_chat_settings("test_chat_123", payload)

        self.assertIn("Both language_name and language_iso_code must be non-empty", str(context.exception))

    def test_save_chat_settings_failure_reply_chance_private_chat(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        private_chat_config = ChatConfig(
            chat_id = UUID(int = 123),
            external_id = "private_chat_123",
            title = "Private Chat",
            language_iso_code = "en",
            reply_chance_percent = 100,
            is_private = True,  # This is the key difference
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
            chat_type = ChatConfigDB.ChatType.telegram,
        )
        self.mock_chat_config_dao.get.return_value = private_chat_config
        self.mock_authorization_service.authorize_for_chat.return_value = private_chat_config

        controller = SettingsController(self.mock_di)
        payload = ChatSettingsPayload(
            language_name = "English",
            language_iso_code = "en",
            reply_chance_percent = 50,  # This should fail for private chats
            release_notifications = "all",
        )

        with self.assertRaises(ValueError) as context:
            controller.save_chat_settings("private_chat_123", payload)

        self.assertIn("Chat is private, reply chance cannot be changed", str(context.exception))

    def test_save_chat_settings_failure_invalid_release_notifications(self):
        self.mock_user_dao.get.return_value = self.invoker_user
        self.mock_chat_config_dao.get.return_value = self.chat_config

        controller = SettingsController(self.mock_di)
        payload = ChatSettingsPayload(
            language_name = "English",
            language_iso_code = "en",
            reply_chance_percent = 50,
            release_notifications = "invalid_value",  # This should fail
        )

        with self.assertRaises(ValueError) as context:
            controller.save_chat_settings("test_chat_123", payload)

        self.assertIn("Invalid release notifications setting value", str(context.exception))

    def test_save_chat_settings_success_all_fields(self):
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
            chat_type = ChatConfigDB.ChatType.telegram,
        )
        self.mock_chat_config_dao.save.return_value = saved_chat_config_db

        controller = SettingsController(self.mock_di)
        payload = ChatSettingsPayload(
            language_name = "Spanish",
            language_iso_code = "es",
            reply_chance_percent = 75,
            release_notifications = "major",
        )

        # Should not raise any exception
        controller.save_chat_settings("test_chat_123", payload)

        # Verify the save method was called
        # noinspection PyUnresolvedReferences
        self.mock_chat_config_dao.save.assert_called_once()

    def test_fetch_admin_chats_success(self):
        self.invoker_user.telegram_chat_id = "invoker_chat_id"  # As in setUp
        own_chat_config = ChatConfig(
            chat_id = UUID(int = 2),
            external_id = str(self.invoker_user.telegram_chat_id),
            title = "My Notes",
            language_iso_code = "en",
            reply_chance_percent = 100,
            is_private = True,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
            chat_type = ChatConfigDB.ChatType.telegram,
        )
        group_chat_config = ChatConfig(
            chat_id = UUID(int = 3),
            external_id = "group_chat_123",
            title = "Test Group",
            language_iso_code = "es",
            reply_chance_percent = 50,
            is_private = False,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
            chat_type = ChatConfigDB.ChatType.telegram,
        )
        no_title_chat_config = ChatConfig(
            chat_id = UUID(int = 4),
            external_id = "no_title_chat_456",
            title = None,
            language_iso_code = "fr",
            reply_chance_percent = 75,
            is_private = False,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
            chat_type = ChatConfigDB.ChatType.telegram,
        )

        self.mock_authorization_service.get_authorized_chats.return_value = [
            own_chat_config,
            group_chat_config,
            no_title_chat_config,
        ]

        controller = SettingsController(self.mock_di)
        result = controller.fetch_admin_chats(self.invoker_user.id.hex)

        self.assertEqual(len(result), 3)

        # Check own chat
        own_chat_result = next(r for r in result if r["chat_id"] == own_chat_config.chat_id.hex)
        self.assertEqual(own_chat_result["title"], "My Notes")
        self.assertTrue(own_chat_result["is_own"])
        self.assertEqual(own_chat_result["platform"], "telegram")

        # Check group chat
        group_chat_result = next(r for r in result if r["chat_id"] == group_chat_config.chat_id.hex)
        self.assertEqual(group_chat_result["title"], "Test Group")
        self.assertFalse(group_chat_result["is_own"])
        self.assertEqual(group_chat_result["platform"], "telegram")

        # Check no title chat
        no_title_result = next(r for r in result if r["chat_id"] == no_title_chat_config.chat_id.hex)
        self.assertIsNone(no_title_result["title"])
        self.assertFalse(no_title_result["is_own"])
        self.assertEqual(no_title_result["platform"], "telegram")

    def test_fetch_admin_chats_no_chats_found(self):
        self.mock_authorization_service.get_authorized_chats.return_value = []

        controller = SettingsController(self.mock_di)
        result = controller.fetch_admin_chats(self.invoker_user.id.hex)

        self.assertEqual(len(result), 0)

    def test_create_settings_link_with_sponsorship(self):
        mock_sponsorship_db = MagicMock()
        mock_sponsorship_db.sponsor_id = UUID("87654321-4321-8765-4321-876543218765")
        mock_sponsorship_db.receiver_id = self.invoker_user.id

        # Create a proper sponsor user DB object with all required fields
        sponsor_user_db = UserDBModel(
            id = UUID("87654321-4321-8765-4321-876543218765"),
            full_name = "Sponsor User",
            telegram_username = "sponsor",
            telegram_chat_id = "987654321",
            telegram_user_id = 987654321,
            group = UserDBModel.Group.developer,
            created_at = datetime.now().date(),
        )

        self.mock_sponsorship_dao.get_all_by_receiver.return_value = [mock_sponsorship_db]
        self.mock_user_dao.get.return_value = sponsor_user_db

        controller = SettingsController(self.mock_di)
        link = controller.create_settings_link()

        self.assertIn("sponsorships", link)
        self.assertIn("user", link)
        self.assertIn(self.invoker_user.id.hex, link)
        self.assertIn("token=", link)

    def test_create_settings_link_no_telegram_chat_id(self):
        user_without_chat = User(
            id = self.invoker_user.id,
            full_name = self.invoker_user.full_name,
            telegram_username = self.invoker_user.telegram_username,
            telegram_chat_id = None,  # No chat ID
            telegram_user_id = None,  # No user ID
            open_ai_key = self.invoker_user.open_ai_key,
            anthropic_key = self.invoker_user.anthropic_key,
            perplexity_key = self.invoker_user.perplexity_key,
            replicate_key = self.invoker_user.replicate_key,
            rapid_api_key = self.invoker_user.rapid_api_key,
            coinmarketcap_key = self.invoker_user.coinmarketcap_key,
            tool_choice_chat = self.invoker_user.tool_choice_chat,
            tool_choice_reasoning = self.invoker_user.tool_choice_reasoning,
            tool_choice_vision = self.invoker_user.tool_choice_vision,
            tool_choice_images_gen = self.invoker_user.tool_choice_images_gen,
            tool_choice_search = self.invoker_user.tool_choice_search,
            group = self.invoker_user.group,
            created_at = self.invoker_user.created_at,
        )

        # noinspection PyPropertyAccess
        type(self.mock_di).invoker = PropertyMock(return_value = user_without_chat)
        controller = SettingsController(self.mock_di)

        with self.assertRaises(ValueError) as context:
            controller.create_settings_link()

        self.assertIn("User never sent a private message, cannot create a settings link", str(context.exception))

    def test_fetch_external_tools_success_mixed_configuration(self):
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
            types = [ToolType.chat],
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

        # Mock the clone method to return a new DI instance
        cloned_di = MagicMock(spec = DI)
        cloned_access_token_resolver = MagicMock()
        cloned_di.access_token_resolver = cloned_access_token_resolver
        self.mock_di.clone.return_value = cloned_di

        # Configure some tools as available, some as not
        def mock_get_token_for_tool(tool):
            return SecretStr("test-token") if tool.id == "configured-tool" else None

        def mock_get_token(provider):
            return SecretStr("test-token") if provider.id == "configured-provider" else None

        cloned_access_token_resolver.get_access_token_for_tool.side_effect = mock_get_token_for_tool
        cloned_access_token_resolver.get_access_token.side_effect = mock_get_token

        with patch("api.settings_controller.ALL_EXTERNAL_TOOLS", [mock_tool_1, mock_tool_2]):
            with patch("api.settings_controller.ALL_PROVIDERS", [mock_provider_1, mock_provider_2]):
                controller = SettingsController(self.mock_di)
                result = controller.fetch_external_tools(self.invoker_user.id.hex)

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

    @patch("api.auth.create_jwt_token")
    def test_create_help_link_success(self, mock_create_jwt_token):
        mock_create_jwt_token.return_value = "test_jwt_token"

        controller = SettingsController(self.mock_di)
        link = controller.create_help_link()

        self.assertIn("features", link)
        self.assertIn("token=", link)
        self.assertIn("en", link)  # Default language
        mock_create_jwt_token.assert_called_once()

    @patch("api.auth.create_jwt_token")
    def test_create_help_link_success_with_custom_language(self, mock_create_jwt_token):
        mock_create_jwt_token.return_value = "test_jwt_token"

        custom_chat_config = ChatConfig(
            chat_id = UUID(int = 2),
            external_id = str(self.invoker_user.telegram_chat_id),
            title = "Test Chat",
            language_iso_code = "es",  # Spanish
            reply_chance_percent = 100,
            is_private = True,
            release_notifications = ChatConfigDB.ReleaseNotifications.all,
            chat_type = ChatConfigDB.ChatType.telegram,
        )
        self.mock_authorization_service.authorize_for_chat.return_value = custom_chat_config

        controller = SettingsController(self.mock_di)
        link = controller.create_help_link()

        self.assertIn("features", link)
        self.assertIn("token=", link)
        self.assertIn("es", link)  # Custom language
        mock_create_jwt_token.assert_called_once()

    def test_create_help_link_failure_no_telegram_chat_id(self):
        user_without_chat = User(
            id = self.invoker_user.id,
            full_name = self.invoker_user.full_name,
            telegram_username = self.invoker_user.telegram_username,
            telegram_chat_id = None,  # No chat ID
            telegram_user_id = None,  # No user ID
            open_ai_key = self.invoker_user.open_ai_key,
            anthropic_key = self.invoker_user.anthropic_key,
            perplexity_key = self.invoker_user.perplexity_key,
            replicate_key = self.invoker_user.replicate_key,
            rapid_api_key = self.invoker_user.rapid_api_key,
            coinmarketcap_key = self.invoker_user.coinmarketcap_key,
            tool_choice_chat = self.invoker_user.tool_choice_chat,
            tool_choice_reasoning = self.invoker_user.tool_choice_reasoning,
            tool_choice_vision = self.invoker_user.tool_choice_vision,
            tool_choice_images_gen = self.invoker_user.tool_choice_images_gen,
            tool_choice_search = self.invoker_user.tool_choice_search,
            group = self.invoker_user.group,
            created_at = self.invoker_user.created_at,
        )

        # noinspection PyPropertyAccess
        type(self.mock_di).invoker = PropertyMock(return_value = user_without_chat)
        controller = SettingsController(self.mock_di)

        with self.assertRaises(ValueError) as context:
            controller.create_help_link()

        self.assertIn("User never sent a private message, cannot create settings link", str(context.exception))
