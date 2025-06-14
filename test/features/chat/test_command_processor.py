import unittest
from datetime import datetime
from unittest.mock import Mock
from uuid import UUID

from api.settings_controller import SettingsController
from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.user import User
from features.chat.command_processor import COMMAND_SETTINGS, COMMAND_START, CommandProcessor
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.prompting.prompt_library import TELEGRAM_BOT_USER
from features.sponsorships.sponsorship_service import SponsorshipService


class CommandProcessorTest(unittest.TestCase):
    user: User
    mock_user_dao: UserCRUD
    mock_sponsorship_service: SponsorshipService
    mock_settings_controller: SettingsController
    mock_telegram_sdk: TelegramBotSDK
    processor: CommandProcessor

    def setUp(self):
        self.user = User(
            id = UUID(int = 1),
            full_name = "Test User",
            telegram_username = "test_username",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = None,
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.mock_user_dao = Mock(spec = UserCRUD)
        self.mock_sponsorship_service = Mock(spec = SponsorshipService)
        self.mock_settings_controller = Mock(spec = SettingsController)
        self.mock_telegram_sdk = Mock(spec = TelegramBotSDK)

        # Setup default return values
        self.mock_sponsorship_service.accept_sponsorship.return_value = False
        self.mock_settings_controller.create_settings_link.return_value = "https://example.com/settings?token=abc123"

        self.processor = CommandProcessor(
            invoker = self.user,
            user_dao = self.mock_user_dao,
            sponsorship_service = self.mock_sponsorship_service,
            settings_controller = self.mock_settings_controller,
            telegram_sdk = self.mock_telegram_sdk,
        )

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
        self.mock_sponsorship_service.accept_sponsorship.assert_called_once_with(self.user)
        # noinspection PyUnresolvedReferences
        self.mock_settings_controller.create_settings_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_telegram_sdk.send_button_link.assert_called_once_with(
            self.user.telegram_chat_id,
            "https://example.com/settings?token=abc123",
        )

    def test_start_command_with_sponsorship(self):
        self.mock_sponsorship_service.accept_sponsorship.return_value = True

        result = self.processor.execute(f"/{COMMAND_START}")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_service.accept_sponsorship.assert_called_once_with(self.user)
        # noinspection PyUnresolvedReferences
        self.mock_settings_controller.create_settings_link.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_telegram_sdk.send_button_link.assert_not_called()

    def test_settings_command(self):
        result = self.processor.execute(f"/{COMMAND_SETTINGS}")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_service.accept_sponsorship.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_settings_controller.create_settings_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_telegram_sdk.send_button_link.assert_called_once_with(
            self.user.telegram_chat_id,
            "https://example.com/settings?token=abc123",
        )

    def test_start_command_with_bot_tag(self):
        bot_tag = TELEGRAM_BOT_USER.telegram_username
        result = self.processor.execute(f"/{COMMAND_START}@{bot_tag}")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_settings_controller.create_settings_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_telegram_sdk.send_button_link.assert_called_once()

    def test_settings_command_with_bot_tag(self):
        bot_tag = TELEGRAM_BOT_USER.telegram_username
        result = self.processor.execute(f"/{COMMAND_SETTINGS}@{bot_tag}")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_settings_controller.create_settings_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_telegram_sdk.send_button_link.assert_called_once()

    def test_wrong_bot_tagged(self):
        result = self.processor.execute(f"/{COMMAND_START}@wrong_bot")
        self.assertEqual(result, CommandProcessor.Result.unknown)
        # noinspection PyUnresolvedReferences
        self.mock_settings_controller.create_settings_link.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_telegram_sdk.send_button_link.assert_not_called()

    def test_unknown_command(self):
        result = self.processor.execute("/unknown_command")
        self.assertEqual(result, CommandProcessor.Result.unknown)
        # noinspection PyUnresolvedReferences
        self.mock_settings_controller.create_settings_link.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_telegram_sdk.send_button_link.assert_not_called()

    def test_start_command_with_arguments_ignored(self):
        result = self.processor.execute(f"/{COMMAND_START} some extra arguments")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_settings_controller.create_settings_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_telegram_sdk.send_button_link.assert_called_once()

    def test_settings_command_with_arguments_ignored(self):
        result = self.processor.execute(f"/{COMMAND_SETTINGS} some extra arguments")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_settings_controller.create_settings_link.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_telegram_sdk.send_button_link.assert_called_once()

    def test_exception_in_settings_controller(self):
        self.mock_settings_controller.create_settings_link.side_effect = Exception("Settings error")

        result = self.processor.execute(f"/{COMMAND_START}")
        self.assertEqual(result, CommandProcessor.Result.failed)

    def test_exception_in_telegram_sdk(self):
        self.mock_telegram_sdk.send_button_link.side_effect = Exception("Telegram error")

        result = self.processor.execute(f"/{COMMAND_START}")
        self.assertEqual(result, CommandProcessor.Result.failed)

    def test_exception_in_sponsorship_service(self):
        self.mock_sponsorship_service.accept_sponsorship.side_effect = Exception("Sponsorship error")

        result = self.processor.execute(f"/{COMMAND_START}")
        self.assertEqual(result, CommandProcessor.Result.failed)
