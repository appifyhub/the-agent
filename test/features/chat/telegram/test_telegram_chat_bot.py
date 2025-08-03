import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import Runnable
from pydantic import SecretStr

from db.model.user import UserDB
from db.schema.chat_config import ChatConfig
from db.schema.user import User
from di.di import DI
from features.chat.command_processor import CommandProcessor
from features.chat.llm_tools.llm_tool_library import LLMToolLibrary
from features.chat.telegram.telegram_chat_bot import TelegramChatBot
from features.chat.telegram.telegram_progress_notifier import TelegramProgressNotifier
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.prompting.prompt_library import TELEGRAM_BOT_USER


class TelegramChatBotTest(unittest.TestCase):

    user: User
    chat_config: ChatConfig
    mock_di: DI
    configured_tool: ConfiguredTool
    bot: TelegramChatBot

    def setUp(self):
        self.user = User(
            id = UUID(int = 1),
            full_name = "Test User",
            telegram_username = "test_user",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = SecretStr("test_openai_key"),
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.chat_config = ChatConfig(
            chat_id = "12345",
            language_iso_code = "en",
            language_name = "English",
            title = "Test Chat",
            is_private = False,
            reply_chance_percent = 50,
        )

        # Create mock DI with all necessary dependencies
        self.mock_di = Mock(spec = DI)
        # noinspection PyPropertyAccess
        self.mock_di.invoker = self.user
        # noinspection PyPropertyAccess
        self.mock_di.invoker_chat = self.chat_config
        # noinspection PyPropertyAccess
        self.mock_di.command_processor = Mock(spec = CommandProcessor)
        # noinspection PyPropertyAccess
        self.mock_di.llm_tool_library = Mock(spec = LLMToolLibrary)
        # noinspection PyPropertyAccess
        self.mock_di.telegram_progress_notifier = Mock(return_value = Mock(spec = TelegramProgressNotifier))
        # noinspection PyPropertyAccess
        self.mock_di.chat_langchain_model = Mock(return_value = Mock(spec = BaseChatModel))

        # Setup method return values
        self.mock_di.llm_tool_library.bind_tools.return_value = Mock(spec = Runnable)
        # noinspection PyPropertyAccess
        self.mock_di.llm_tool_library.tool_names = ["test_tool"]

        # noinspection PyTypeChecker
        self.configured_tool = Mock(spec = ConfiguredTool)

        self.bot = TelegramChatBot(
            messages = [HumanMessage("Test message")],
            raw_last_message = "Test message",
            last_message_id = "msg_123",
            attachment_ids = [],
            configured_tool = self.configured_tool,
            di = self.mock_di,
        )

    def test_process_commands_no_api_key(self):
        # Create bot without configured_tool
        bot_no_key = TelegramChatBot(
            messages = [HumanMessage("Test message")],
            raw_last_message = "Test message",
            last_message_id = "msg_123",
            attachment_ids = [],
            configured_tool = None,
            di = self.mock_di,
        )

        self.mock_di.command_processor.execute.return_value = CommandProcessor.Result.unknown

        result, status = bot_no_key.process_commands()

        self.assertIsInstance(result, AIMessage)
        self.assertEqual(status, CommandProcessor.Result.unknown)
        self.assertEqual(result.content, "")

    def test_process_commands_failed(self):
        self.mock_di.command_processor.execute.return_value = CommandProcessor.Result.failed

        result, status = self.bot.process_commands()

        self.assertIsInstance(result, AIMessage)
        self.assertEqual(status, CommandProcessor.Result.failed)
        self.assertIn("Unknown command.", result.content)

    def test_process_commands_success(self):
        self.mock_di.command_processor.execute.return_value = CommandProcessor.Result.success

        result, status = self.bot.process_commands()

        self.assertIsInstance(result, AIMessage)
        self.assertEqual(status, CommandProcessor.Result.success)
        self.assertEqual(result.content, "")

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

    # noinspection PyUnresolvedReferences
    def test_should_not_reply_to_self(self):
        self.chat_config.is_private = False
        self.chat_config.reply_chance_percent = 100
        self.bot._TelegramChatBot__raw_last_message = "Hello"
        self.mock_di.invoker.telegram_username = TELEGRAM_BOT_USER.telegram_username

        self.assertFalse(self.bot.should_reply())

    # noinspection PyUnresolvedReferences
    def test_should_reply_to_other_user(self):
        self.chat_config.is_private = False
        self.chat_config.reply_chance_percent = 100
        self.bot._TelegramChatBot__raw_last_message = "Hello"
        self.mock_di.invoker.telegram_username = "other_user"

        self.assertTrue(self.bot.should_reply())

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_no_reply_needed(self, mock_should_reply):
        mock_should_reply.return_value = False
        result = self.bot.execute()
        self.assertIsNone(result)

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.process_commands")
    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_command_processed(self, mock_should_reply, mock_process_commands):
        mock_should_reply.return_value = True
        mock_process_commands.return_value = (AIMessage(""), CommandProcessor.Result.success)
        result = self.bot.execute()
        self.assertIsNone(result)

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.process_commands")
    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_command_failed(self, mock_should_reply, mock_process_commands):
        mock_should_reply.return_value = True
        mock_process_commands.return_value = (AIMessage("Unknown command."), CommandProcessor.Result.failed)
        result = self.bot.execute()
        self.assertEqual(result, AIMessage("Unknown command."))

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.process_commands")
    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_no_api_key(self, mock_should_reply, mock_process_commands):
        mock_should_reply.return_value = True
        mock_process_commands.return_value = (AIMessage(""), CommandProcessor.Result.unknown)

        # Create a new bot instance without configured_tool (simulating no API key)
        bot_no_key = TelegramChatBot(
            messages = [HumanMessage("Test message")],
            raw_last_message = "Test message",
            last_message_id = "msg_123",
            attachment_ids = [],
            configured_tool = None,
            di = self.mock_di,
        )

        result = bot_no_key.execute()
        self.assertIn("Not configured", result.content)

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.process_commands")
    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_llm_response(self, mock_should_reply, mock_process_commands):
        mock_should_reply.return_value = True
        mock_process_commands.return_value = (AIMessage(""), CommandProcessor.Result.unknown)

        # Mock the tools_model invoke to return the final response
        mock_tools_model = Mock()
        mock_tools_model.invoke.return_value = AIMessage("LLM response")
        self.mock_di.llm_tool_library.bind_tools.return_value = mock_tools_model

        result = self.bot.execute()
        self.assertEqual(result.content, "LLM response")

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.process_commands")
    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_tool_call(self, mock_should_reply, mock_process_commands):
        mock_should_reply.return_value = True
        mock_process_commands.return_value = (AIMessage(""), CommandProcessor.Result.unknown)
        tool_call = {"id": "1", "name": "test_tool", "args": {}}

        # Create AI messages with tool_calls attribute
        ai_with_tools = AIMessage(content = "", tool_calls = [tool_call])
        ai_final = AIMessage("Final response")

        # Mock the tools_model to return first tool calls, then final response
        mock_tools_model = Mock()
        mock_tools_model.invoke.side_effect = [ai_with_tools, ai_final]
        self.mock_di.llm_tool_library.bind_tools.return_value = mock_tools_model
        self.mock_di.llm_tool_library.invoke.return_value = "Tool result"

        result = self.bot.execute()
        self.assertEqual(result.content, "Final response")

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.process_commands")
    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_exception(self, mock_should_reply, mock_process_commands):
        mock_should_reply.return_value = True
        mock_process_commands.return_value = (AIMessage(""), CommandProcessor.Result.unknown)

        # Mock the tools_model to raise an exception
        mock_tools_model = Mock()
        mock_tools_model.invoke.side_effect = Exception("Test error")
        self.mock_di.llm_tool_library.bind_tools.return_value = mock_tools_model

        result = self.bot.execute()
        self.assertIn("⚡", result.content)
        self.assertIn("Test error", result.content)
        self.assertIn("/settings", result.content)

    @patch("features.chat.telegram.telegram_chat_bot.config")
    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.process_commands")
    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_max_iterations_exceeded(self, mock_should_reply, mock_process_commands, mock_config):
        mock_should_reply.return_value = True
        mock_process_commands.return_value = (AIMessage(""), CommandProcessor.Result.unknown)
        mock_config.max_chatbot_iterations = 2

        # Create AI messages with tool_calls to simulate continued iterations
        tool_call = {"id": "1", "name": "test_tool", "args": {}}
        ai_with_tools = AIMessage(content = "", tool_calls = [tool_call])

        # Make the LLM always return messages with tool calls to continue iterations
        mock_tools_model = Mock()
        mock_tools_model.invoke.return_value = ai_with_tools
        self.mock_di.llm_tool_library.bind_tools.return_value = mock_tools_model
        self.mock_di.llm_tool_library.invoke.return_value = "Tool result"

        result = self.bot.execute()

        # The OverflowError should be caught and converted to an AIMessage with error content
        self.assertIsInstance(result, AIMessage)
        self.assertIn("⚡", result.content)  # Error indicator
        self.assertIn("Reached max iterations", result.content)
        self.assertIn("2", result.content)  # Should include the max iterations count
