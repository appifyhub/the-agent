import unittest
from datetime import date
from unittest.mock import Mock, patch
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import Runnable

from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.user import User
from features.chat.telegram.telegram_chat_bot import TelegramChatBot
from features.chat.tools.predefined_tools import PredefinedTools
from features.command_processor import CommandProcessor
from features.prompting.predefined_prompts import TELEGRAM_BOT_USER


class TelegramChatBotTest(unittest.TestCase):
    user: User
    chat_config: ChatConfig
    command_processor_mock: CommandProcessor
    predefined_tools_mock: PredefinedTools
    llm_base_mock: BaseChatModel
    llm_tools_mock: Runnable
    bot: TelegramChatBot

    def setUp(self):
        self.user = User(
            id = UUID(int = 1),
            created_at = date.today(),
            full_name = "Test User",
            telegram_username = "test_user",
            telegram_chat_id = "12345",
            telegram_user_id = 67890,
            open_ai_key = "test_key",
            group = UserDB.Group.standard,
        )
        self.chat_config = ChatConfig(
            chat_id = "12345",
            language_iso_code = "en",
            language_name = "English",
            title = "Test Chat",
            is_private = False,
            reply_chance_percent = 50,
        )
        self.command_processor_mock = Mock(spec = CommandProcessor)
        self.predefined_tools_mock = Mock(spec = PredefinedTools)
        self.llm_base_mock = Mock(spec = BaseChatModel)
        self.llm_tools_mock = Mock(spec = Runnable)

        self.bot = TelegramChatBot(
            self.chat_config,
            self.user,
            [HumanMessage("Test message")],
            "Test message",
            self.command_processor_mock,
        )
        self.bot._TelegramChatBot__predefined_tools = self.predefined_tools_mock
        self.bot._TelegramChatBot__llm_base = self.llm_base_mock
        self.bot._TelegramChatBot__llm_tools = self.llm_tools_mock

    def test_process_commands_no_api_key(self):
        self.user.open_ai_key = None
        self.command_processor_mock.execute.return_value = CommandProcessor.Result.unknown

        result, status = self.bot.process_commands()

        self.assertIsInstance(result, AIMessage)
        self.assertEqual(status, CommandProcessor.Result.unknown)
        self.assertIn("It's not a valid format.", result.content)

    def test_process_commands_failed(self):
        self.command_processor_mock.execute.return_value = CommandProcessor.Result.failed

        result, status = self.bot.process_commands()

        self.assertIsInstance(result, AIMessage)
        self.assertEqual(status, CommandProcessor.Result.failed)
        self.assertIn("It's not a known failure.", result.content)

    def test_process_commands_success(self):
        self.command_processor_mock.execute.return_value = CommandProcessor.Result.success

        result, status = self.bot.process_commands()

        self.assertIsInstance(result, AIMessage)
        self.assertEqual(status, CommandProcessor.Result.success)
        self.assertIn("Thanks, we can try again now", result.content)

    def test_should_reply_private_chat(self):
        self.chat_config.is_private = True
        self.chat_config.reply_chance_percent = 0
        self.bot._TelegramChatBot__raw_last_message = "Hello"

        self.assertTrue(self.bot.should_reply())

    def test_should_reply_bot_mentioned(self):
        self.chat_config.is_private = False
        self.chat_config.reply_chance_percent = 0
        self.bot._TelegramChatBot__raw_last_message = f"Hello @{TELEGRAM_BOT_USER.telegram_username}"

        self.assertTrue(self.bot.should_reply())

    @patch("random.randint")
    def test_should_reply_random_chance(self, mock_randint):
        self.chat_config.is_private = False
        self.chat_config.reply_chance_percent = 50
        self.bot._TelegramChatBot__raw_last_message = "Hello"

        mock_randint.return_value = 25
        self.assertTrue(self.bot.should_reply())

        mock_randint.return_value = 75
        self.assertFalse(self.bot.should_reply())

    def test_should_not_reply_empty_message(self):
        self.chat_config.is_private = True
        self.chat_config.reply_chance_percent = 100
        self.bot._TelegramChatBot__raw_last_message = " "

        self.assertFalse(self.bot.should_reply())

    def test_should_not_reply_zero_chance(self):
        self.chat_config.is_private = False
        self.chat_config.reply_chance_percent = 0
        self.bot._TelegramChatBot__raw_last_message = "Hello"

        self.assertFalse(self.bot.should_reply())

    def test_should_not_reply_100_chance(self):
        self.chat_config.is_private = False
        self.chat_config.reply_chance_percent = 100
        self.bot._TelegramChatBot__raw_last_message = "Hello"

        self.assertTrue(self.bot.should_reply())

    def test_should_reply_group_chat(self):
        self.chat_config.is_private = False
        self.chat_config.title = "Group Chat"
        self.chat_config.reply_chance_percent = 100
        self.bot._TelegramChatBot__raw_last_message = "Hello"

        self.assertTrue(self.bot.should_reply())

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_no_reply_needed(self, mock_should_reply):
        mock_should_reply.return_value = False
        result = self.bot.execute()
        self.assertEqual(result, AIMessage(""))

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.process_commands")
    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_command_processed(self, mock_should_reply, mock_process_commands):
        mock_should_reply.return_value = True
        mock_process_commands.return_value = (AIMessage("Command processed"), CommandProcessor.Result.success)
        result = self.bot.execute()
        self.assertEqual(result, AIMessage("Command processed"))

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.process_commands")
    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_no_api_key(self, mock_should_reply, mock_process_commands):
        mock_should_reply.return_value = True
        mock_process_commands.return_value = (AIMessage("No API key"), CommandProcessor.Result.unknown)
        # noinspection PyUnresolvedReferences
        self.bot._TelegramChatBot__invoker.open_ai_key = None
        result = self.bot.execute()
        self.assertEqual(result, AIMessage("No API key"))

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.process_commands")
    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_llm_response(self, mock_should_reply, mock_process_commands):
        mock_should_reply.return_value = True
        mock_process_commands.return_value = (AIMessage(""), CommandProcessor.Result.unknown)
        self.llm_tools_mock.invoke.return_value = AIMessage("LLM response")
        result = self.bot.execute()
        self.assertEqual(result, AIMessage("LLM response"))

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.process_commands")
    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_tool_call(self, mock_should_reply, mock_process_commands):
        mock_should_reply.return_value = True
        mock_process_commands.return_value = (AIMessage(""), CommandProcessor.Result.unknown)
        tool_call = {"id": "1", "name": "test_tool", "args": {}}
        self.llm_tools_mock.invoke.side_effect = [
            AIMessage(content = "", tool_calls = [tool_call]),
            AIMessage("Final response")
        ]
        self.predefined_tools_mock.invoke.return_value = "Tool result"
        result = self.bot.execute()
        self.assertEqual(result, AIMessage("Final response"))

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.process_commands")
    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_exception(self, mock_should_reply, mock_process_commands):
        mock_should_reply.return_value = True
        mock_process_commands.return_value = (AIMessage(""), CommandProcessor.Result.unknown)
        self.llm_tools_mock.invoke.side_effect = Exception("Test error")
        result = self.bot.execute()
        self.assertIn("I'm having issues replying to you", result.content)
        self.assertIn("Test error", result.content)
