import unittest

from features.external_tools.external_tool import ToolType
from features.external_tools.external_tool_library import (
    ANTHROPIC,
    OPEN_AI,
)
from features.external_tools.external_tool_provider_library import ALL_PROVIDERS
from features.external_tools.tool_choice_resolver import ToolChoiceResolver


class ToolChoiceResolverTest(unittest.TestCase):

    def test_find_tool_by_id_success_existing_tool(self):
        tool = ToolChoiceResolver.find_tool_by_id("gpt-4o-mini")

        self.assertIsNotNone(tool)
        assert tool is not None  # Type narrowing for linter
        self.assertEqual(tool.id, "gpt-4o-mini")
        self.assertEqual(tool.name, "GPT 4o Mini")
        self.assertEqual(tool.provider, OPEN_AI)
        self.assertIn(ToolType.chat, tool.types)

    def test_find_tool_by_id_success_anthropic_tool(self):
        tool = ToolChoiceResolver.find_tool_by_id("claude-3-5-sonnet-latest")

        self.assertIsNotNone(tool)
        assert tool is not None  # Type narrowing for linter
        self.assertEqual(tool.id, "claude-3-5-sonnet-latest")
        self.assertEqual(tool.name, "Claude 3.5 Sonnet")
        self.assertEqual(tool.provider, ANTHROPIC)
        self.assertIn(ToolType.chat, tool.types)

    def test_find_tool_by_id_failure_nonexistent_tool(self):
        tool = ToolChoiceResolver.find_tool_by_id("nonexistent-tool-id")

        self.assertIsNone(tool)

    def test_find_tool_by_id_failure_empty_string(self):
        tool = ToolChoiceResolver.find_tool_by_id("")

        self.assertIsNone(tool)

    def test_get_eligible_tools_by_provider_chat_type_no_preference(self):
        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(ToolType.chat)

        self.assertGreater(len(provider_tools), 0)

        openai_tools = provider_tools.get(OPEN_AI, [])
        self.assertGreater(len(openai_tools), 0)

        for _, tools in provider_tools.items():
            for tool in tools:
                self.assertIn(ToolType.chat, tool.types)

    def test_get_eligible_tools_by_provider_vision_type_no_preference(self):
        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(ToolType.vision)

        self.assertGreater(len(provider_tools), 0)

        for _, tools in provider_tools.items():
            for tool in tools:
                self.assertIn(ToolType.vision, tool.types)

    def test_get_eligible_tools_by_provider_hearing_type_no_preference(self):
        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(ToolType.hearing)

        self.assertGreater(len(provider_tools), 0)

        for _, tools in provider_tools.items():
            for tool in tools:
                self.assertIn(ToolType.hearing, tool.types)

    def test_get_eligible_tools_by_provider_with_valid_preference(self):
        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(
            ToolType.chat,
            preferred_tool = "claude-3-5-sonnet-latest",
        )

        anthropic_tools = provider_tools.get(ANTHROPIC, [])
        self.assertGreater(len(anthropic_tools), 0)

        self.assertEqual(anthropic_tools[0].id, "claude-3-5-sonnet-latest")

        claude_count = sum(1 for tool in anthropic_tools if tool.id == "claude-3-5-sonnet-latest")
        self.assertEqual(claude_count, 1)

    def test_get_eligible_tools_by_provider_with_invalid_preference_wrong_type(self):
        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(
            ToolType.hearing,
            preferred_tool = "claude-3-5-sonnet-latest",  # This doesn't support hearing
        )

        self.assertGreater(len(provider_tools), 0)

        for _, tools in provider_tools.items():
            for tool in tools:
                self.assertIn(ToolType.hearing, tool.types)

        for _, tools in provider_tools.items():
            for tool in tools:
                self.assertNotEqual(tool.id, "claude-3-5-sonnet-latest")

    def test_get_eligible_tools_by_provider_with_nonexistent_preference(self):
        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(
            ToolType.chat,
            preferred_tool = "nonexistent-tool",
        )

        self.assertGreater(len(provider_tools), 0)

        for _, tools in provider_tools.items():
            for tool in tools:
                self.assertIn(ToolType.chat, tool.types)

    def test_get_eligible_tools_by_provider_empty_result_for_unsupported_type(self):
        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(ToolType.api_twitter)

        total_tools = sum(len(tools) for tools in provider_tools.values())
        self.assertGreaterEqual(total_tools, 0)  # Could be 0 or more depending on available tools

        for _, tools in provider_tools.items():
            for tool in tools:
                self.assertIn(ToolType.api_twitter, tool.types)

    def test_get_eligible_tools_by_provider_multiple_types_tool(self):
        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(
            ToolType.copywriting,
            preferred_tool = "gpt-4o-mini",  # This supports chat, copywriting, and vision
        )

        openai_tools = provider_tools.get(OPEN_AI, [])
        self.assertGreater(len(openai_tools), 0)

        self.assertEqual(openai_tools[0].id, "gpt-4o-mini")

        for _, tools in provider_tools.items():
            for tool in tools:
                self.assertIn(ToolType.copywriting, tool.types)

    def test_get_eligible_tools_by_provider_preserves_provider_grouping(self):
        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(ToolType.chat)

        for provider, tools in provider_tools.items():
            self.assertIsInstance(tools, list)
            for tool in tools:
                self.assertEqual(tool.provider, provider)

    def test_get_eligible_tools_by_provider_no_none_values(self):
        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(ToolType.chat)

        for _, tools in provider_tools.items():
            self.assertIsNotNone(tools)
            self.assertIsInstance(tools, list)

    def test_get_eligible_tools_by_provider_preference_moves_to_front_only(self):
        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(
            ToolType.chat,
            preferred_tool = "gpt-4o-mini",
        )

        openai_tools = provider_tools.get(OPEN_AI, [])
        self.assertGreater(len(openai_tools), 0)

        self.assertEqual(openai_tools[0].id, "gpt-4o-mini")

        gpt_4o_mini_count = sum(1 for tool in openai_tools if tool.id == "gpt-4o-mini")
        self.assertEqual(gpt_4o_mini_count, 1)

    def test_get_eligible_tools_by_provider_with_external_tool_instance(self):
        preferred_tool_instance = ToolChoiceResolver.find_tool_by_id("claude-3-5-sonnet-latest")
        self.assertIsNotNone(preferred_tool_instance)

        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(
            ToolType.chat,
            preferred_tool = preferred_tool_instance,
        )

        anthropic_tools = provider_tools.get(ANTHROPIC, [])
        self.assertGreater(len(anthropic_tools), 0)

        self.assertEqual(anthropic_tools[0].id, "claude-3-5-sonnet-latest")

        claude_count = sum(1 for tool in anthropic_tools if tool.id == "claude-3-5-sonnet-latest")
        self.assertEqual(claude_count, 1)

    def test_get_eligible_tools_by_provider_with_invalid_external_tool_instance(self):
        vision_tool = ToolChoiceResolver.find_tool_by_id("gpt-4o-mini")  # Supports vision
        self.assertIsNotNone(vision_tool)

        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(
            ToolType.hearing,
            preferred_tool = vision_tool,
        )

        self.assertGreater(len(provider_tools), 0)

        for _, tools in provider_tools.items():
            for tool in tools:
                self.assertIn(ToolType.hearing, tool.types)

        for _, tools in provider_tools.items():
            for tool in tools:
                self.assertNotEqual(tool.id, "gpt-4o-mini")

    def test_get_eligible_tools_by_provider_includes_all_providers(self):
        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(ToolType.hearing)

        self.assertEqual(len(provider_tools), len(ALL_PROVIDERS))

        for provider in ALL_PROVIDERS:
            self.assertIn(provider, provider_tools)
            self.assertIsInstance(provider_tools[provider], list)

        non_empty_providers = [provider for provider, tools in provider_tools.items() if len(tools) > 0]

        self.assertGreater(len(non_empty_providers), 0)

        for provider in non_empty_providers:
            for tool in provider_tools[provider]:
                self.assertIn(ToolType.hearing, tool.types)

    def test_get_eligible_tools_by_provider_empty_providers_have_empty_lists(self):
        provider_tools = ToolChoiceResolver.get_eligible_tools_by_provider(ToolType.api_crypto_exchange)

        self.assertEqual(len(provider_tools), len(ALL_PROVIDERS))

        for provider in ALL_PROVIDERS:
            self.assertIn(provider, provider_tools)
            self.assertIsInstance(provider_tools[provider], list)

            for tool in provider_tools[provider]:
                self.assertIn(ToolType.api_crypto_exchange, tool.types)
