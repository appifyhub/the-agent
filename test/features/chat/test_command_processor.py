import unittest
from datetime import datetime
from unittest.mock import Mock
from uuid import UUID

from api.settings_controller import SettingsController
from db.crud.user import UserCRUD
from db.model.chat_config import ChatConfigDB
from db.model.user import UserDB
from db.schema.user import User, UserSave
from di.di import DI
from features.chat.command_processor import COMMAND_HELP, COMMAND_SETTINGS, COMMAND_START, CommandProcessor
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.integrations.integrations import resolve_agent_user
from features.sponsorships.sponsorship_service import SponsorshipService


class CommandProcessorTest(unittest.TestCase):

    user: User
    agent_user: UserSave
    mock_di: DI
    processor: CommandProcessor

    def setUp(self):
        self.user = User(
            id = UUID(int = 1),
            full_name = "Test User",
            telegram_username = "test_username",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.agent_user = resolve_agent_user(ChatConfigDB.ChatType.telegram)

        # Create mock DI with all required dependencies
        self.mock_di = Mock(spec = DI)
        # noinspection PyPropertyAccess
        self.mock_di.invoker = self.user

        # noinspection PyPropertyAccess
        self.mock_di.user_crud = Mock(spec = UserCRUD)
        # noinspection PyPropertyAccess
        self.mock_di.sponsorship_service = Mock(spec = SponsorshipService)
        # noinspection PyPropertyAccess
        self.mock_di.settings_controller = Mock(spec = SettingsController)
        # noinspection PyPropertyAccess
        self.mock_di.telegram_bot_sdk = Mock(spec = TelegramBotSDK)

        # Setup default return values
        self.mock_di.sponsorship_service.accept_sponsorship.return_value = False
        self.mock_di.settings_controller.create_settings_link.return_value = "https://example.com/settings?token=abc123"
        self.mock_di.settings_controller.create_help_link.return_value = "https://example.com/features?token=abc123"

        self.processor = CommandProcessor(self.mock_di)

    def test_empty_input(self):
        result = self.processor.execute("")
        self.assertEqual(result, CommandProcessor.Result.unknown)

    def test_non_command_input(self):
        result = self.processor.execute("This is not a command")
        self.assertEqual(result, CommandProcessor.Result.unknown)

    def test_start_command_no_sponsorship(self):
        result = self.processor.execute(f"/{COMMAND_START}")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_di.sponsorship_service.accept_sponsorship.assert_called_once_with(self.user)
        # noinspection PyUnresolvedReferences
        self.mock_di.settings_controller.create_settings_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_button_link.assert_called_once_with(
            self.user.telegram_chat_id,
            "https://example.com/settings?token=abc123",
        )

    def test_start_command_with_sponsorship(self):
        self.mock_di.sponsorship_service.accept_sponsorship.return_value = True

        result = self.processor.execute(f"/{COMMAND_START}")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_di.sponsorship_service.accept_sponsorship.assert_called_once_with(self.user)
        # noinspection PyUnresolvedReferences
        self.mock_di.settings_controller.create_settings_link.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_button_link.assert_not_called()

    def test_settings_command(self):
        result = self.processor.execute(f"/{COMMAND_SETTINGS}")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_di.sponsorship_service.accept_sponsorship.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_di.settings_controller.create_settings_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_button_link.assert_called_once_with(
            self.user.telegram_chat_id,
            "https://example.com/settings?token=abc123",
        )

    def test_start_command_with_bot_tag(self):
        bot_tag = self.agent_user.telegram_username
        result = self.processor.execute(f"/{COMMAND_START}@{bot_tag}")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_di.settings_controller.create_settings_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_button_link.assert_called_once()

    def test_settings_command_with_bot_tag(self):
        bot_tag = self.agent_user.telegram_username
        result = self.processor.execute(f"/{COMMAND_SETTINGS}@{bot_tag}")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_di.settings_controller.create_settings_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_button_link.assert_called_once()

    def test_wrong_bot_tagged(self):
        result = self.processor.execute(f"/{COMMAND_START}@wrong_bot")
        self.assertEqual(result, CommandProcessor.Result.unknown)
        # noinspection PyUnresolvedReferences
        self.mock_di.settings_controller.create_settings_link.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_button_link.assert_not_called()

    def test_unknown_command(self):
        result = self.processor.execute("/unknown_command")
        self.assertEqual(result, CommandProcessor.Result.unknown)
        # noinspection PyUnresolvedReferences
        self.mock_di.settings_controller.create_settings_link.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_button_link.assert_not_called()

    def test_start_command_with_arguments_ignored(self):
        result = self.processor.execute(f"/{COMMAND_START} some extra arguments")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_di.settings_controller.create_settings_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_button_link.assert_called_once()

    def test_settings_command_with_arguments_ignored(self):
        result = self.processor.execute(f"/{COMMAND_SETTINGS} some extra arguments")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_di.settings_controller.create_settings_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_button_link.assert_called_once()

    def test_exception_in_settings_controller(self):
        self.mock_di.settings_controller.create_settings_link.side_effect = Exception("Settings error")

        result = self.processor.execute(f"/{COMMAND_START}")
        self.assertEqual(result, CommandProcessor.Result.failed)

    def test_exception_in_telegram_sdk(self):
        self.mock_di.telegram_bot_sdk.send_button_link.side_effect = Exception("Telegram error")

        result = self.processor.execute(f"/{COMMAND_START}")
        self.assertEqual(result, CommandProcessor.Result.failed)

    def test_exception_in_sponsorship_service(self):
        self.mock_di.sponsorship_service.accept_sponsorship.side_effect = Exception("Sponsorship error")

        result = self.processor.execute(f"/{COMMAND_START}")
        self.assertEqual(result, CommandProcessor.Result.failed)

    def test_help_command(self):
        result = self.processor.execute(f"/{COMMAND_HELP}")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_di.settings_controller.create_help_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_button_link.assert_called_once_with(
            self.user.telegram_chat_id,
            "https://example.com/features?token=abc123",
        )

    def test_help_command_with_bot_tag(self):
        bot_tag = self.agent_user.telegram_username
        result = self.processor.execute(f"/{COMMAND_HELP}@{bot_tag}")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_di.settings_controller.create_help_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_button_link.assert_called_once()

    def test_help_command_with_arguments_ignored(self):
        result = self.processor.execute(f"/{COMMAND_HELP} some extra arguments")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_di.settings_controller.create_help_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_button_link.assert_called_once()

    def test_exception_in_help_link_creation(self):
        self.mock_di.settings_controller.create_help_link.side_effect = Exception("Help link error")

        result = self.processor.execute(f"/{COMMAND_HELP}")
        self.assertEqual(result, CommandProcessor.Result.failed)
