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
from features.chat.command_processor import CommandProcessor
from features.chat.llm_tools.llm_tool_library import LLMToolLibrary
from features.chat.telegram.telegram_chat_bot import TelegramChatBot
from features.chat.telegram.telegram_progress_notifier import TelegramProgressNotifier
from features.external_tools.access_token_resolver import AccessTokenResolver
from features.prompting.prompt_library import TELEGRAM_BOT_USER


class TelegramChatBotTest(unittest.TestCase):
    user: User
    chat_config: ChatConfig
    access_token_resolver_mock: AccessTokenResolver
    command_processor_mock: CommandProcessor
    progress_notifier_mock: TelegramProgressNotifier
    llm_tool_library_mock: LLMToolLibrary
    llm_base_mock: BaseChatModel
    llm_tools_mock: Runnable
    bot: TelegramChatBot

    def setUp(self):
        self.user = User(
            id = UUID(int = 1),
            full_name = "Test User",
            telegram_username = "test_user",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = "test_openai_key",
            anthropic_key = None,
            perplexity_key = None,
            replicate_key = None,
            rapid_api_key = None,
            coinmarketcap_key = None,
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
        self.access_token_resolver_mock = Mock(spec = AccessTokenResolver)
        self.command_processor_mock = Mock(spec = CommandProcessor)
        self.progress_notifier_mock = Mock(spec = TelegramProgressNotifier)
        self.llm_tool_library_mock = Mock(spec = LLMToolLibrary)
        self.llm_base_mock = Mock(spec = BaseChatModel)
        self.llm_tools_mock = Mock(spec = Runnable)

        self.access_token_resolver_mock.get_access_token_for_tool.return_value = SecretStr("test_token")
        self.bot = TelegramChatBot(
            self.chat_config,
            self.user,
            [HumanMessage("Test message")],
            [],  # attachment_ids
            "Test message",
            self.command_processor_mock,
            self.progress_notifier_mock,
            self.access_token_resolver_mock,
        )
        self.bot._TelegramChatBot__llm_tool_library = self.llm_tool_library_mock
        self.bot._TelegramChatBot__llm_base = self.llm_base_mock
        self.bot._TelegramChatBot__llm_tools = self.llm_tools_mock

    def test_process_commands_no_api_key(self):
        self.access_token_resolver_mock.get_access_token_for_tool.return_value = None
        self.command_processor_mock.execute.return_value = CommandProcessor.Result.unknown

        result, status = self.bot.process_commands()

        self.assertIsInstance(result, AIMessage)
        self.assertEqual(status, CommandProcessor.Result.unknown)
        self.assertEqual(result.content, "")

    def test_process_commands_failed(self):
        self.command_processor_mock.execute.return_value = CommandProcessor.Result.failed

        result, status = self.bot.process_commands()

        self.assertIsInstance(result, AIMessage)
        self.assertEqual(status, CommandProcessor.Result.failed)
        self.assertIn("Unknown command.", result.content)

    def test_process_commands_success(self):
        self.command_processor_mock.execute.return_value = CommandProcessor.Result.success

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
        self.bot._TelegramChatBot__invoker.telegram_username = TELEGRAM_BOT_USER.telegram_username

        self.assertFalse(self.bot.should_reply())

    # noinspection PyUnresolvedReferences
    def test_should_reply_to_other_user(self):
        self.chat_config.is_private = False
        self.chat_config.reply_chance_percent = 100
        self.bot._TelegramChatBot__raw_last_message = "Hello"
        self.bot._TelegramChatBot__invoker.telegram_username = "other_user"

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
        self.access_token_resolver_mock.get_access_token_for_tool.return_value = None
        self.bot._TelegramChatBot__llm_has_access_token = False
        result = self.bot.execute()
        self.assertIn("Not configured", result.content)

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

        # Create AI messages with tool_calls attribute
        ai_with_tools = AIMessage(content = "", tool_calls = [tool_call])
        ai_final = AIMessage("Final response")

        self.llm_tools_mock.invoke.side_effect = [ai_with_tools, ai_final]
        self.llm_tool_library_mock.invoke.return_value = "Tool result"
        result = self.bot.execute()
        self.assertEqual(result.content, "Final response")

    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.process_commands")
    @patch("features.chat.telegram.telegram_chat_bot.TelegramChatBot.should_reply")
    def test_execute_exception(self, mock_should_reply, mock_process_commands):
        mock_should_reply.return_value = True
        mock_process_commands.return_value = (AIMessage(""), CommandProcessor.Result.unknown)
        self.llm_tools_mock.invoke.side_effect = Exception("Test error")
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
        self.llm_tools_mock.invoke.return_value = ai_with_tools
        self.llm_tool_library_mock.invoke.return_value = "Tool result"

        result = self.bot.execute()

        # The OverflowError should be caught and converted to an AIMessage with error content
        self.assertIsInstance(result, AIMessage)
        self.assertIn("⚡", result.content)  # Error indicator
        self.assertIn("Reached max iterations", result.content)
        self.assertIn("2", result.content)  # Should include the max iterations count
