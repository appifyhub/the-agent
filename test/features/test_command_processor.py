import unittest
from datetime import datetime
from unittest.mock import Mock
from uuid import UUID

from db.model.user import UserDB
from db.schema.user import User
from features.command_processor import CommandProcessor
from features.prompting.prompt_library import TELEGRAM_BOT_USER, COMMAND_START


class CommandProcessorTest(unittest.TestCase):
    user: User
    mock_user_dao: Mock
    mock_invite_manager: Mock
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
        self.mock_user_dao = Mock()
        self.mock_invite_manager = Mock()
        self.mock_invite_manager.purge_accepted_invites.return_value = 0
        self.mock_invite_manager.accept_invite.return_value = 0
        self.mock_user_dao.save.return_value = User(**self.user.model_dump())
        self.processor = CommandProcessor(self.user, self.mock_user_dao, self.mock_invite_manager)

    def test_empty_input(self):
        result = self.processor.execute("")
        self.assertEqual(result, CommandProcessor.Result.unknown)

    def test_non_command_input(self):
        result = self.processor.execute("This is not a command")
        self.assertEqual(result, CommandProcessor.Result.unknown)

    def test_start_command_no_key(self):
        result = self.processor.execute(f"/{COMMAND_START}")
        self.assertEqual(result, CommandProcessor.Result.unknown)
        self.mock_user_dao.save.assert_not_called()

    def test_wrong_bot_tagged(self):
        result = self.processor.execute(f"/{COMMAND_START}@wrong_bot api_key_here")
        self.assertEqual(result, CommandProcessor.Result.unknown)

    def test_exception_handling(self):
        self.mock_user_dao.save.side_effect = Exception("Test exception")
        result = self.processor.execute(f"/{COMMAND_START} api_key_here")
        self.assertEqual(result, CommandProcessor.Result.failed)
        self.mock_invite_manager.accept_invite.assert_called_once_with(self.user)

    def test_start_command_success(self):
        self.mock_invite_manager.accept_invite.return_value = False
        result = self.processor.execute(f"/{COMMAND_START} api_key_here")
        self.assertEqual(result, CommandProcessor.Result.success)
        self.mock_user_dao.save.assert_called_once()
        self.mock_invite_manager.purge_accepted_invites.assert_called_once_with(self.user)

    def test_start_command_success_with_bot_tag(self):
        self.mock_invite_manager.accept_invite.return_value = False
        bot_tag = TELEGRAM_BOT_USER.telegram_username
        result = self.processor.execute(f"/{COMMAND_START}@{bot_tag} api_key_here")
        self.assertEqual(result, CommandProcessor.Result.success)
        self.mock_user_dao.save.assert_called_once()
        self.mock_invite_manager.purge_accepted_invites.assert_called_once_with(self.user)

    def test_accept_invite_success(self):
        self.mock_invite_manager.accept_invite.return_value = True
        result = self.processor.execute(f"/{COMMAND_START} api_key_here")
        self.assertEqual(result, CommandProcessor.Result.success)
        self.mock_invite_manager.accept_invite.assert_called_once_with(self.user)
        self.mock_user_dao.save.assert_not_called()
        self.mock_invite_manager.purge_accepted_invites.assert_not_called()
