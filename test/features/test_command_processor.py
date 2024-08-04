import unittest
from datetime import datetime
from unittest.mock import Mock
from uuid import UUID

from db.model.user import UserDB
from db.schema.user import User
from features.command_processor import CommandProcessor
from features.prompting.predefined_prompts import TELEGRAM_BOT_USER, COMMAND_START


class CommandProcessorTest(unittest.TestCase):
    __user: User
    __mock_user_dao: Mock
    __processor: CommandProcessor

    def setUp(self):
        self.__user = User(
            id = UUID(int = 1),
            full_name = "Test User",
            telegram_username = "test_username",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = None,
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.__mock_user_dao = Mock()
        self.__processor = CommandProcessor(self.__user, self.__mock_user_dao)

    def test_empty_input(self):
        result = self.__processor.execute("")
        self.assertEqual(result, CommandProcessor.Result.unknown)

    def test_non_command_input(self):
        result = self.__processor.execute("This is not a command")
        self.assertEqual(result, CommandProcessor.Result.unknown)

    def test_start_command_no_key(self):
        result = self.__processor.execute(f"/{COMMAND_START}")
        self.assertEqual(result, CommandProcessor.Result.unknown)
        self.__mock_user_dao.save.assert_not_called()

    def test_wrong_bot_tagged(self):
        result = self.__processor.execute(f"/{COMMAND_START}@wrong_bot api_key_here")
        self.assertEqual(result, CommandProcessor.Result.unknown)

    def test_exception_handling(self):
        self.__mock_user_dao.save.side_effect = Exception("Test exception")
        result = self.__processor.execute(f"/{COMMAND_START} api_key_here")
        self.assertEqual(result, CommandProcessor.Result.failed)

    def test_start_command_success(self):
        result = self.__processor.execute(f"/{COMMAND_START} api_key_here")
        self.assertEqual(result, CommandProcessor.Result.success)
        self.__mock_user_dao.save.assert_called_once()

    def test_start_command_success_with_bot_tag(self):
        bot_tag = TELEGRAM_BOT_USER.telegram_username
        result = self.__processor.execute(f"/{COMMAND_START}@{bot_tag} api_key_here")
        self.assertEqual(result, CommandProcessor.Result.success)
        self.__mock_user_dao.save.assert_called_once()
