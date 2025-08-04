import unittest
from datetime import datetime
from unittest.mock import Mock
from uuid import UUID

from pydantic import SecretStr

from db.model.user import UserDB
from db.schema.user import User
from di.di import DI
from features.external_tools.access_token_resolver import AccessTokenResolver
from features.external_tools.external_tool import ToolType
from features.external_tools.external_tool_library import CLAUDE_3_5_SONNET, GPT_4O_MINI
from features.external_tools.tool_choice_resolver import ToolChoiceResolver, ToolResolutionError


class ToolChoiceResolverTest(unittest.TestCase):

    invoker_user: User
    mock_access_token_resolver: Mock
    mock_di: DI

    def setUp(self):
        self.invoker_user = User(
            id = UUID(int = 1),
            full_name = "Test User",
            telegram_username = "test_user",
            telegram_chat_id = "test_chat_id",
            telegram_user_id = 1,
            open_ai_key = SecretStr("test_openai_key"),
            anthropic_key = SecretStr("test_anthropic_key"),
            tool_choice_chat = "claude-3-5-sonnet-latest",
            tool_choice_vision = "gpt-4o-mini",
            group = UserDB.Group.standard,
            created_at = datetime.now().date(),
        )
        self.mock_access_token_resolver = Mock(spec = AccessTokenResolver)
        self.mock_di = Mock(spec = DI)
        # noinspection PyPropertyAccess
        self.mock_di.invoker = self.invoker_user
        # noinspection PyPropertyAccess
        self.mock_di.access_token_resolver = self.mock_access_token_resolver

    def test_find_tool_by_id_success_existing_tool(self):
        tool = ToolChoiceResolver.find_tool_by_id(GPT_4O_MINI.id)
        self.assertEqual(tool, GPT_4O_MINI)

    def test_find_tool_by_id_success_anthropic_tool(self):
        tool = ToolChoiceResolver.find_tool_by_id(CLAUDE_3_5_SONNET.id)
        self.assertEqual(tool, CLAUDE_3_5_SONNET)

    def test_find_tool_by_id_failure_nonexistent_tool(self):
        tool = ToolChoiceResolver.find_tool_by_id("nonexistent-tool-id")
        self.assertIsNone(tool)

    def test_find_tool_by_id_failure_empty_string(self):
        tool = ToolChoiceResolver.find_tool_by_id("")
        self.assertIsNone(tool)

    def test_get_prioritized_tools_no_user_choice_no_default(self):
        tools = ToolChoiceResolver.get_prioritized_tools(
            ToolType.chat,
            user_choice_tool = None,
            default_tool = None,
        )

        self.assertGreater(len(tools), 1)
        for tool in tools:
            self.assertIn(ToolType.chat, tool.types)

    def test_get_prioritized_tools_only_user_choice(self):
        tools = ToolChoiceResolver.get_prioritized_tools(
            ToolType.chat,
            user_choice_tool = CLAUDE_3_5_SONNET,
            default_tool = None,
        )

        self.assertGreater(len(tools), 1)
        self.assertEqual(tools[0], CLAUDE_3_5_SONNET)
        for tool in tools:
            self.assertIn(ToolType.chat, tool.types)

    def test_get_prioritized_tools_only_default(self):
        tools = ToolChoiceResolver.get_prioritized_tools(
            ToolType.chat,
            user_choice_tool = None,
            default_tool = CLAUDE_3_5_SONNET,
        )

        self.assertGreater(len(tools), 1)
        self.assertEqual(tools[0], CLAUDE_3_5_SONNET)
        for tool in tools:
            self.assertIn(ToolType.chat, tool.types)

    def test_get_prioritized_tools_both_user_choice_and_default(self):
        tools = ToolChoiceResolver.get_prioritized_tools(
            ToolType.chat,
            user_choice_tool = CLAUDE_3_5_SONNET.id,
            default_tool = GPT_4O_MINI.id,
        )

        self.assertGreater(len(tools), 2)
        self.assertEqual(tools[0], CLAUDE_3_5_SONNET)
        self.assertEqual(tools[1], GPT_4O_MINI)
        for tool in tools:
            self.assertIn(ToolType.chat, tool.types)

    def test_get_prioritized_tools_user_choice_same_as_default_no_duplication(self):
        tools = ToolChoiceResolver.get_prioritized_tools(
            ToolType.chat,
            user_choice_tool = GPT_4O_MINI,
            default_tool = GPT_4O_MINI,
        )

        self.assertGreater(len(tools), 1)
        self.assertEqual(tools[0], GPT_4O_MINI)

        gpt_4o_mini_count = sum(1 for tool in tools if tool == GPT_4O_MINI)
        self.assertEqual(gpt_4o_mini_count, 1)

    def test_get_prioritized_tools_invalid_user_choice_tool_type(self):
        tools = ToolChoiceResolver.get_prioritized_tools(
            ToolType.hearing,
            user_choice_tool = GPT_4O_MINI,
        )

        self.assertGreater(len(tools), 0)
        self.assertNotEqual(tools[0], GPT_4O_MINI)
        for tool in tools:
            self.assertIn(ToolType.hearing, tool.types)

    def test_get_prioritized_tools_nonexistent_tools_ignored(self):
        tools = ToolChoiceResolver.get_prioritized_tools(
            ToolType.chat,
            user_choice_tool = "nonexistent-user-tool",
            default_tool = "nonexistent-default-tool",
        )

        self.assertGreater(len(tools), 1)
        for tool in tools:
            self.assertIn(ToolType.chat, tool.types)

    def test_get_tool_success_user_has_access_to_user_choice(self):
        self.mock_access_token_resolver.get_access_token_for_tool.return_value = SecretStr("test_token")

        resolver = ToolChoiceResolver(self.mock_di)
        result = resolver.get_tool(ToolType.chat)

        self.assertIsNotNone(result)
        assert result is not None  # Type hint for linter
        tool, token, purpose = result
        self.assertEqual(tool, CLAUDE_3_5_SONNET)
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), "test_token")
        self.assertEqual(purpose, ToolType.chat)

    def test_get_tool_success_user_no_access_to_user_choice_but_has_access_to_others(self):
        def mock_get_access_token_for_tool(test_tool):
            if test_tool == CLAUDE_3_5_SONNET:
                return None
            return SecretStr("test_token")

        self.mock_access_token_resolver.get_access_token_for_tool.side_effect = mock_get_access_token_for_tool

        resolver = ToolChoiceResolver(self.mock_di)
        result = resolver.get_tool(ToolType.chat)

        self.assertIsNotNone(result)
        assert result is not None  # Type hint for linter
        tool, token, purpose = result
        self.assertNotEqual(tool, CLAUDE_3_5_SONNET)
        self.assertIn(ToolType.chat, tool.types)
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), "test_token")
        self.assertEqual(purpose, ToolType.chat)

    def test_get_tool_success_with_default_tool_prioritized(self):
        def mock_get_access_token_for_tool(test_tool):
            if test_tool == CLAUDE_3_5_SONNET:
                return None
            if test_tool == GPT_4O_MINI:
                return SecretStr("test_token")
            return None

        self.mock_access_token_resolver.get_access_token_for_tool.side_effect = mock_get_access_token_for_tool

        resolver = ToolChoiceResolver(self.mock_di)
        result = resolver.get_tool(ToolType.chat, default_tool = GPT_4O_MINI.id)

        self.assertIsNotNone(result)
        assert result is not None  # Type hint for linter
        tool, token, purpose = result
        self.assertEqual(tool, GPT_4O_MINI)
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), "test_token")
        self.assertEqual(purpose, ToolType.chat)

    def test_get_tool_failure_no_access_to_any_tool(self):
        self.mock_access_token_resolver.get_access_token_for_tool.return_value = None

        resolver = ToolChoiceResolver(self.mock_di)
        result = resolver.get_tool(ToolType.chat)

        self.assertIsNone(result)

    def test_require_tool_success(self):
        self.mock_access_token_resolver.get_access_token_for_tool.return_value = SecretStr("test_token")

        resolver = ToolChoiceResolver(self.mock_di)
        result = resolver.require_tool(ToolType.chat)

        self.assertIsNotNone(result)
        assert result is not None  # Type hint for linter
        tool, token, purpose = result
        self.assertEqual(tool, CLAUDE_3_5_SONNET)
        self.assertIsInstance(token, SecretStr)
        self.assertEqual(token.get_secret_value(), "test_token")
        self.assertEqual(purpose, ToolType.chat)

    def test_require_tool_failure_raises_exception(self):
        self.mock_access_token_resolver.get_access_token_for_tool.return_value = None

        resolver = ToolChoiceResolver(self.mock_di)

        with self.assertRaises(ToolResolutionError) as context:
            resolver.require_tool(ToolType.chat)

        error_message = str(context.exception)
        self.assertIn("Unable to resolve a tool for 'chat'", error_message)
        self.assertIn(str(self.invoker_user.id.hex), error_message)

    def test_user_tool_choice_mapping_through_public_interface(self):
        self.mock_access_token_resolver.get_access_token_for_tool.return_value = SecretStr("test_token_1")

        resolver = ToolChoiceResolver(self.mock_di)

        chat_result = resolver.get_tool(ToolType.chat)
        self.assertIsNotNone(chat_result)
        assert chat_result is not None  # Type hint for linter
        chat_tool, chat_token, chat_purpose = chat_result
        self.assertEqual(chat_tool, CLAUDE_3_5_SONNET)
        self.assertIsInstance(chat_token, SecretStr)
        self.assertEqual(chat_token.get_secret_value(), "test_token_1")
        self.assertEqual(chat_purpose, ToolType.chat)

        self.mock_access_token_resolver.get_access_token_for_tool.return_value = SecretStr("test_token_2")

        vision_result = resolver.get_tool(ToolType.vision)
        self.assertIsNotNone(vision_result)
        assert vision_result is not None  # Type hint for linter
        vision_tool, vision_token, vision_purpose = vision_result
        self.assertEqual(vision_tool, GPT_4O_MINI)
        self.assertIsInstance(vision_token, SecretStr)
        self.assertEqual(vision_token.get_secret_value(), "test_token_2")
        self.assertEqual(vision_purpose, ToolType.vision)
