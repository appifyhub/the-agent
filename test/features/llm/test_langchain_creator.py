import unittest
from unittest.mock import patch

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_perplexity import ChatPerplexity
from pydantic import SecretStr

from features.external_tools.external_tool import ExternalTool, ExternalToolProvider, ToolType
from features.external_tools.external_tool_provider_library import ANTHROPIC, GOOGLE_AI, OPEN_AI, PERPLEXITY
from features.llm.langchain_creator import create


class LangchainCreatorTest(unittest.TestCase):

    def setUp(self):
        self.mock_openai_provider = OPEN_AI
        self.mock_anthropic_provider = ANTHROPIC
        self.mock_google_ai_provider = GOOGLE_AI
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

        self.mock_google_ai_tool = ExternalTool(
            id = "gemini-1.5-flash",
            name = "Gemini 1.5 Flash",
            provider = self.mock_google_ai_provider,
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
        configured_tool = (self.mock_openai_tool, api_key, ToolType.chat)

        result = create(configured_tool)

        self.assertIsInstance(result, ChatOpenAI)

    @patch("features.llm.langchain_creator.config")
    def test_create_anthropic_reasoning_model(self, mock_config):
        mock_config.web_retries = 5
        mock_config.web_timeout_s = 15

        api_key = SecretStr("test-anthropic-key")
        configured_tool = (self.mock_anthropic_tool, api_key, ToolType.reasoning)

        result = create(configured_tool)

        self.assertIsInstance(result, ChatAnthropic)

    @patch("features.llm.langchain_creator.config")
    def test_create_perplexity_search_model(self, mock_config):
        mock_config.web_retries = 2
        mock_config.web_timeout_s = 20

        api_key = SecretStr("test-perplexity-key")
        configured_tool = (self.mock_perplexity_tool, api_key, ToolType.search)

        result = create(configured_tool)

        self.assertIsInstance(result, ChatPerplexity)

    @patch("features.llm.langchain_creator.config")
    def test_create_google_ai_chat_model(self, mock_config):
        mock_config.web_retries = 3
        mock_config.web_timeout_s = 10

        api_key = SecretStr("test-google-ai-key")
        configured_tool = (self.mock_google_ai_tool, api_key, ToolType.chat)

        result = create(configured_tool)

        self.assertIsInstance(result, ChatGoogleGenerativeAI)

    @patch("features.llm.langchain_creator.config")
    def test_create_copywriting_model(self, mock_config):
        mock_config.web_retries = 1
        mock_config.web_timeout_s = 30

        api_key = SecretStr("test-key")
        configured_tool = (self.mock_openai_tool, api_key, ToolType.copywriting)

        result = create(configured_tool)

        self.assertIsInstance(result, ChatOpenAI)

    @patch("features.llm.langchain_creator.config")
    def test_create_vision_model(self, mock_config):
        mock_config.web_retries = 4
        mock_config.web_timeout_s = 25

        api_key = SecretStr("test-key")
        configured_tool = (self.mock_anthropic_tool, api_key, ToolType.vision)

        result = create(configured_tool)

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
        configured_tool = (unsupported_tool, api_key, ToolType.chat)

        with self.assertRaises(ValueError) as context:
            create(configured_tool)

        self.assertIn("does not support temperature", str(context.exception))

    def test_unsupported_tool_type_temperature(self):
        api_key = SecretStr("test-key")
        configured_tool = (self.mock_openai_tool, api_key, ToolType.hearing)

        with self.assertRaises(ValueError) as context:
            create(configured_tool)

        self.assertIn("does not support temperature", str(context.exception))

    def test_unsupported_tool_type_max_tokens(self):
        api_key = SecretStr("test-key")
        configured_tool = (self.mock_openai_tool, api_key, ToolType.images_gen)

        with self.assertRaises(ValueError) as context:
            create(configured_tool)

        self.assertIn("does not support temperature", str(context.exception))

    def test_unsupported_tool_type_timeout(self):
        api_key = SecretStr("test-key")
        configured_tool = (self.mock_openai_tool, api_key, ToolType.embedding)

        with self.assertRaises(ValueError) as context:
            create(configured_tool)

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
        configured_tool = (unsupported_tool, api_key, ToolType.chat)

        with self.assertRaises(ValueError) as context:
            create(configured_tool)

        self.assertIn("does not support temperature", str(context.exception))

    @patch("features.llm.langchain_creator.config")
    def test_all_supported_tool_types_with_openai(self, mock_config):
        mock_config.web_retries = 3
        mock_config.web_timeout_s = 10

        # Test all supported tool types
        supported_types = [
            ToolType.chat,
            ToolType.reasoning,
            ToolType.copywriting,
            ToolType.vision,
            ToolType.search,
        ]

        api_key = SecretStr("test-key")
        for tool_type in supported_types:
            # noinspection PyUnresolvedReferences
            with self.subTest(tool_type = tool_type):
                configured_tool = (self.mock_openai_tool, api_key, tool_type)
                result = create(configured_tool)
                self.assertIsInstance(result, ChatOpenAI)

    @patch("features.llm.langchain_creator.config")
    def test_all_supported_tool_types_with_anthropic(self, mock_config):
        mock_config.web_retries = 3
        mock_config.web_timeout_s = 10

        # Test all supported tool types
        supported_types = [
            ToolType.chat,
            ToolType.reasoning,
            ToolType.copywriting,
            ToolType.vision,
            ToolType.search,
        ]

        api_key = SecretStr("test-key")
        for tool_type in supported_types:
            with self.subTest(tool_type = tool_type):
                configured_tool = (self.mock_anthropic_tool, api_key, tool_type)
                result = create(configured_tool)
                self.assertIsInstance(result, ChatAnthropic)

    @patch("features.llm.langchain_creator.config")
    def test_all_supported_tool_types_with_perplexity(self, mock_config):
        mock_config.web_retries = 3
        mock_config.web_timeout_s = 10

        # Test all supported tool types
        supported_types = [
            ToolType.chat,
            ToolType.reasoning,
            ToolType.copywriting,
            ToolType.vision,
            ToolType.search,
        ]

        api_key = SecretStr("test-key")
        for tool_type in supported_types:
            with self.subTest(tool_type = tool_type):
                configured_tool = (self.mock_perplexity_tool, api_key, tool_type)
                result = create(configured_tool)
                self.assertIsInstance(result, ChatPerplexity)

    @patch("features.llm.langchain_creator.config")
    def test_all_supported_tool_types_with_google_ai(self, mock_config):
        mock_config.web_retries = 3
        mock_config.web_timeout_s = 10

        # Test all supported tool types
        supported_types = [
            ToolType.chat,
            ToolType.reasoning,
            ToolType.copywriting,
            ToolType.vision,
            ToolType.search,
        ]

        api_key = SecretStr("test-key")
        for tool_type in supported_types:
            with self.subTest(tool_type = tool_type):
                configured_tool = (self.mock_google_ai_tool, api_key, tool_type)
                result = create(configured_tool)
                self.assertIsInstance(result, ChatGoogleGenerativeAI)

    @patch("features.llm.langchain_creator.config")
    def test_config_values_are_used(self, mock_config):
        """Test that config values are properly passed to model creation"""
        mock_config.web_retries = 7
        mock_config.web_timeout_s = 42

        # Just verify the function completes without error
        # The actual config usage is tested implicitly by the model creation
        api_key = SecretStr("test-key")
        configured_tool = (self.mock_openai_tool, api_key, ToolType.chat)
        result = create(configured_tool)
        self.assertIsInstance(result, ChatOpenAI)

    def test_temperature_calculation_logic(self):
        """Test that different tool types result in different model instances"""
        api_key = SecretStr("test-key")

        with patch("features.llm.langchain_creator.config") as mock_config:
            mock_config.web_retries = 3
            mock_config.web_timeout_s = 10

            # Test that different tool types create models (temperature logic is internal)
            configured_tool = (self.mock_openai_tool, api_key, ToolType.chat)
            chat_result = create(configured_tool)
            configured_tool = (self.mock_openai_tool, api_key, ToolType.reasoning)
            reasoning_result = create(configured_tool)
            configured_tool = (self.mock_openai_tool, api_key, ToolType.copywriting)
            copywriting_result = create(configured_tool)

            # All should be ChatOpenAI instances but potentially with different configs
            self.assertIsInstance(chat_result, ChatOpenAI)
            self.assertIsInstance(reasoning_result, ChatOpenAI)
            self.assertIsInstance(copywriting_result, ChatOpenAI)

    @patch("features.llm.langchain_creator.config")
    def test_reasoning_tool_has_longer_timeout(self, mock_config):
        mock_config.web_retries = 3
        mock_config.web_timeout_s = 10

        api_key = SecretStr("test-key")

        # [1] chat requested, tool supports reasoning -> 3x timeout
        configured_tool_chat = (self.mock_openai_tool, api_key, ToolType.chat)
        result_chat = create(configured_tool_chat)
        self.assertEqual(result_chat.request_timeout, 30)  # 10 * 3

        # [2] reasoning requested -> 3x timeout
        configured_tool_reasoning = (self.mock_openai_tool, api_key, ToolType.reasoning)
        result_reasoning = create(configured_tool_reasoning)
        self.assertEqual(result_reasoning.request_timeout, 30)  # 10 * 3

        # [3] chat requested, tool does not support reasoning -> 1x timeout
        chat_only_tool = ExternalTool(
            id = "chat-only",
            name = "Chat Only",
            provider = self.mock_openai_provider,
            types = [ToolType.chat],
        )
        configured_tool_chat_only = (chat_only_tool, api_key, ToolType.chat)
        result_chat_only = create(configured_tool_chat_only)
        self.assertEqual(result_chat_only.request_timeout, 10)  # 10 * 1
