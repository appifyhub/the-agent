import unittest
from datetime import datetime
from unittest.mock import Mock
from uuid import UUID

from db.crud.user import UserCRUD
from db.model.user import UserDB
from db.schema.user import User
from features.chat.command_processor import CommandProcessor
from features.chat.sponsorship_manager import SponsorshipManager
from features.prompting.prompt_library import TELEGRAM_BOT_USER, COMMAND_START


class CommandProcessorTest(unittest.TestCase):
    user: User
    mock_user_dao: UserCRUD
    mock_sponsorship_manager: SponsorshipManager
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
        self.mock_user_dao.save.return_value = User(**self.user.model_dump())
        self.mock_sponsorship_manager = Mock(spec = SponsorshipManager)
        self.mock_sponsorship_manager.purge_accepted_sponsorships.return_value = 0
        self.mock_sponsorship_manager.accept_sponsorship.return_value = 0
        self.processor = CommandProcessor(self.user, self.mock_user_dao, self.mock_sponsorship_manager)

    def test_empty_input(self):
        result = self.processor.execute("")
        self.assertEqual(result, CommandProcessor.Result.unknown)

    def test_non_command_input(self):
        result = self.processor.execute("This is not a command")
        self.assertEqual(result, CommandProcessor.Result.unknown)

    def test_start_command_no_key(self):
        result = self.processor.execute(f"/{COMMAND_START}")
        self.assertEqual(result, CommandProcessor.Result.unknown)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.save.assert_not_called()

    def test_wrong_bot_tagged(self):
        result = self.processor.execute(f"/{COMMAND_START}@wrong_bot api_key_here")
        self.assertEqual(result, CommandProcessor.Result.unknown)

    def test_exception_handling(self):
        self.mock_user_dao.save.side_effect = Exception("Test exception")
        result = self.processor.execute(f"/{COMMAND_START} api_key_here")
        self.assertEqual(result, CommandProcessor.Result.failed)
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_manager.accept_sponsorship.assert_called_once_with(self.user)

    def test_start_command_success(self):
        self.mock_sponsorship_manager.accept_sponsorship.return_value = False
        result = self.processor.execute(f"/{COMMAND_START} api_key_here")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.save.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_manager.purge_accepted_sponsorships.assert_called_once_with(self.user)

    def test_start_command_success_with_bot_tag(self):
        self.mock_sponsorship_manager.accept_sponsorship.return_value = False
        bot_tag = TELEGRAM_BOT_USER.telegram_username
        result = self.processor.execute(f"/{COMMAND_START}@{bot_tag} api_key_here")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.save.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_manager.purge_accepted_sponsorships.assert_called_once_with(self.user)

    def test_accept_sponsorship_success(self):
        self.mock_sponsorship_manager.accept_sponsorship.return_value = True
        result = self.processor.execute(f"/{COMMAND_START} api_key_here")
        self.assertEqual(result, CommandProcessor.Result.success)
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_manager.accept_sponsorship.assert_called_once_with(self.user)
        # noinspection PyUnresolvedReferences
        self.mock_user_dao.save.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_sponsorship_manager.purge_accepted_sponsorships.assert_not_called()
