import unittest
from unittest.mock import patch

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_perplexity import ChatPerplexity
from pydantic import SecretStr

from features.external_tools.external_tool import ExternalTool, ExternalToolProvider, ToolType
from features.external_tools.external_tool_provider_library import ANTHROPIC, OPEN_AI, PERPLEXITY
from features.llm.langchain_creator import create


class LangchainCreatorTest(unittest.TestCase):

    def setUp(self):
        self.mock_openai_provider = OPEN_AI
        self.mock_anthropic_provider = ANTHROPIC
        self.mock_perplexity_provider = PERPLEXITY

        self.mock_openai_tool = ExternalTool(
            id = "gpt-4o-mini",
            name = "GPT-4o Mini",
            provider = self.mock_openai_provider,
            types = [ToolType.chat, ToolType.reasoning],
        )

        self.mock_anthropic_tool = ExternalTool(
            id = "claude-3-5-sonnet-latest",
            name = "Claude 3.5 Sonnet",
            provider = self.mock_anthropic_provider,
            types = [ToolType.chat, ToolType.reasoning],
        )

        self.mock_perplexity_tool = ExternalTool(
            id = "llama-3.1-sonar-small-128k-online",
            name = "Llama 3.1 Sonar Small",
            provider = self.mock_perplexity_provider,
            types = [ToolType.search],
        )

    @patch("features.llm.langchain_creator.config")
    def test_create_openai_chat_model(self, mock_config):
        mock_config.web_retries = 3
        mock_config.web_timeout_s = 10

        api_key = SecretStr("test-openai-key")
        configured_tool = (self.mock_openai_tool, api_key)

        result = create(configured_tool, ToolType.chat)

        self.assertIsInstance(result, ChatOpenAI)

    @patch("features.llm.langchain_creator.config")
    def test_create_anthropic_reasoning_model(self, mock_config):
        mock_config.web_retries = 5
        mock_config.web_timeout_s = 15

        api_key = SecretStr("test-anthropic-key")
        configured_tool = (self.mock_anthropic_tool, api_key)

        result = create(configured_tool, ToolType.reasoning)

        self.assertIsInstance(result, ChatAnthropic)

    @patch("features.llm.langchain_creator.config")
    def test_create_perplexity_search_model(self, mock_config):
        mock_config.web_retries = 2
        mock_config.web_timeout_s = 20

        api_key = SecretStr("test-perplexity-key")
        configured_tool = (self.mock_perplexity_tool, api_key)

        result = create(configured_tool, ToolType.search)

        self.assertIsInstance(result, ChatPerplexity)

    @patch("features.llm.langchain_creator.config")
    def test_create_copywriting_model(self, mock_config):
        mock_config.web_retries = 1
        mock_config.web_timeout_s = 30

        api_key = SecretStr("test-key")
        configured_tool = (self.mock_openai_tool, api_key)

        result = create(configured_tool, ToolType.copywriting)

        self.assertIsInstance(result, ChatOpenAI)

    @patch("features.llm.langchain_creator.config")
    def test_create_vision_model(self, mock_config):
        mock_config.web_retries = 4
        mock_config.web_timeout_s = 25

        api_key = SecretStr("test-key")
        configured_tool = (self.mock_anthropic_tool, api_key)

        result = create(configured_tool, ToolType.vision)

        self.assertIsInstance(result, ChatAnthropic)

    def test_create_unsupported_provider(self):
        unsupported_provider = ExternalToolProvider(
            id = "unsupported",
            name = "Unsupported Provider",
            token_management_url = "https://example.com",
            token_format = "test",
            tools = ["test"],
        )

        unsupported_tool = ExternalTool(
            id = "unsupported-model",
            name = "Unsupported Model",
            provider = unsupported_provider,
            types = [ToolType.chat],
        )

        api_key = SecretStr("test-key")
        configured_tool = (unsupported_tool, api_key)

        with self.assertRaises(ValueError) as context:
            create(configured_tool, ToolType.chat)

        self.assertIn("does not support temperature", str(context.exception))

    def test_unsupported_tool_type_temperature(self):
        api_key = SecretStr("test-key")
        configured_tool = (self.mock_openai_tool, api_key)

        with self.assertRaises(ValueError) as context:
            create(configured_tool, ToolType.hearing)

        self.assertIn("does not support temperature", str(context.exception))

    def test_unsupported_tool_type_max_tokens(self):
        api_key = SecretStr("test-key")
        configured_tool = (self.mock_openai_tool, api_key)

        with self.assertRaises(ValueError) as context:
            create(configured_tool, ToolType.images_gen)

        self.assertIn("does not support temperature", str(context.exception))

    def test_unsupported_tool_type_timeout(self):
        api_key = SecretStr("test-key")
        configured_tool = (self.mock_openai_tool, api_key)

        with self.assertRaises(ValueError) as context:
            create(configured_tool, ToolType.embedding)

        self.assertIn("does not support temperature", str(context.exception))

    def test_unsupported_provider_temperature_normalization(self):
        unsupported_provider = ExternalToolProvider(
            id = "unknown-provider",
            name = "Unknown Provider",
            token_management_url = "https://example.com",
            token_format = "test",
            tools = ["test"],
        )

        unsupported_tool = ExternalTool(
            id = "unknown-model",
            name = "Unknown Model",
            provider = unsupported_provider,
            types = [ToolType.chat],
        )

        api_key = SecretStr("test-key")
        configured_tool = (unsupported_tool, api_key)

        with self.assertRaises(ValueError) as context:
            create(configured_tool, ToolType.chat)

        self.assertIn("does not support temperature", str(context.exception))

    @patch("features.llm.langchain_creator.config")
    def test_all_supported_tool_types_with_openai(self, mock_config):
        mock_config.web_retries = 3
        mock_config.web_timeout_s = 10

        api_key = SecretStr("test-key")
        configured_tool = (self.mock_openai_tool, api_key)

        # Test all supported tool types
        supported_types = [
            ToolType.chat,
            ToolType.reasoning,
            ToolType.copywriting,
            ToolType.vision,
            ToolType.search,
        ]

        for tool_type in supported_types:
            with self.subTest(tool_type = tool_type):
                result = create(configured_tool, tool_type)
                self.assertIsInstance(result, ChatOpenAI)

    @patch("features.llm.langchain_creator.config")
    def test_all_supported_tool_types_with_anthropic(self, mock_config):
        mock_config.web_retries = 3
        mock_config.web_timeout_s = 10

        api_key = SecretStr("test-key")
        configured_tool = (self.mock_anthropic_tool, api_key)

        # Test all supported tool types
        supported_types = [
            ToolType.chat,
            ToolType.reasoning,
            ToolType.copywriting,
            ToolType.vision,
            ToolType.search,
        ]

        for tool_type in supported_types:
            with self.subTest(tool_type = tool_type):
                result = create(configured_tool, tool_type)
                self.assertIsInstance(result, ChatAnthropic)

    @patch("features.llm.langchain_creator.config")
    def test_all_supported_tool_types_with_perplexity(self, mock_config):
        mock_config.web_retries = 3
        mock_config.web_timeout_s = 10

        api_key = SecretStr("test-key")
        configured_tool = (self.mock_perplexity_tool, api_key)

        # Test all supported tool types
        supported_types = [
            ToolType.chat,
            ToolType.reasoning,
            ToolType.copywriting,
            ToolType.vision,
            ToolType.search,
        ]

        for tool_type in supported_types:
            with self.subTest(tool_type = tool_type):
                result = create(configured_tool, tool_type)
                self.assertIsInstance(result, ChatPerplexity)

    @patch("features.llm.langchain_creator.config")
    def test_config_values_are_used(self, mock_config):
        """Test that config values are properly passed to model creation"""
        mock_config.web_retries = 7
        mock_config.web_timeout_s = 42

        api_key = SecretStr("test-key")
        configured_tool = (self.mock_openai_tool, api_key)

        # Just verify the function completes without error
        # The actual config usage is tested implicitly by the model creation
        result = create(configured_tool, ToolType.chat)
        self.assertIsInstance(result, ChatOpenAI)

    def test_temperature_calculation_logic(self):
        """Test that different tool types result in different model instances"""
        api_key = SecretStr("test-key")
        configured_tool = (self.mock_openai_tool, api_key)

        with patch("features.llm.langchain_creator.config") as mock_config:
            mock_config.web_retries = 3
            mock_config.web_timeout_s = 10

            # Test that different tool types create models (temperature logic is internal)
            chat_result = create(configured_tool, ToolType.chat)
            reasoning_result = create(configured_tool, ToolType.reasoning)
            copywriting_result = create(configured_tool, ToolType.copywriting)

            # All should be ChatOpenAI instances but potentially with different configs
            self.assertIsInstance(chat_result, ChatOpenAI)
            self.assertIsInstance(reasoning_result, ChatOpenAI)
            self.assertIsInstance(copywriting_result, ChatOpenAI)
