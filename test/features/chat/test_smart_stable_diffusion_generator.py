import unittest
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from di.di import DI
from features.chat.smart_stable_diffusion_generator import SmartStableDiffusionGenerator
from features.external_tools.tool_choice_resolver import ConfiguredTool


class SmartStableDiffusionGeneratorTest(unittest.TestCase):
    raw_prompt: str
    mock_di: DI
    mock_configured_copywriter_tool: ConfiguredTool
    mock_configured_image_gen_tool: ConfiguredTool

    def setUp(self):
        self.raw_prompt = "Generate a beautiful landscape"

        # Mock DI
        self.mock_di = MagicMock()
        self.mock_di.invoker_chat.chat_id = "test_chat_id"
        self.mock_di.telegram_bot_sdk.send_photo.return_value = {"result": {"message_id": 123}}

        # Mock text_stable_diffusion_generator method
        self.simple_stable_diffusion_generator = MagicMock()
        self.mock_di.simple_stable_diffusion_generator.return_value = self.simple_stable_diffusion_generator

        # Mock configured tools
        # noinspection PyTypeChecker
        self.mock_configured_copywriter_tool = MagicMock(spec = ConfiguredTool)
        # noinspection PyTypeChecker
        self.mock_configured_image_gen_tool = MagicMock(spec = ConfiguredTool)

    def test_init_success(self):
        generator = SmartStableDiffusionGenerator(
            self.raw_prompt,
            self.mock_configured_copywriter_tool,
            self.mock_configured_image_gen_tool,
            self.mock_di,
        )
        self.assertIsInstance(generator, SmartStableDiffusionGenerator)

    def test_execute_success(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined prompt")
        self.mock_di.chat_langchain_model.return_value = mock_llm

        self.simple_stable_diffusion_generator.execute.return_value = "http://example.com/image.png"

        generator = SmartStableDiffusionGenerator(
            self.raw_prompt,
            self.mock_configured_copywriter_tool,
            self.mock_configured_image_gen_tool,
            self.mock_di,
        )
        result = generator.execute()

        self.assertEqual(result, SmartStableDiffusionGenerator.Result.success)
        mock_llm.invoke.assert_called_once()
        self.simple_stable_diffusion_generator.execute.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_photo.assert_called_once_with("test_chat_id", "http://example.com/image.png")

    def test_execute_llm_failure(self):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM error")
        self.mock_di.chat_langchain_model.return_value = mock_llm

        generator = SmartStableDiffusionGenerator(
            self.raw_prompt,
            self.mock_configured_copywriter_tool,
            self.mock_configured_image_gen_tool,
            self.mock_di,
        )
        result = generator.execute()

        self.assertEqual(result, SmartStableDiffusionGenerator.Result.failed)
        mock_llm.invoke.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_photo.assert_not_called()

    def test_execute_image_generation_failure(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined prompt")
        self.mock_di.chat_langchain_model.return_value = mock_llm

        self.simple_stable_diffusion_generator.execute.return_value = None

        generator = SmartStableDiffusionGenerator(
            self.raw_prompt,
            self.mock_configured_copywriter_tool,
            self.mock_configured_image_gen_tool,
            self.mock_di,
        )
        result = generator.execute()

        self.assertEqual(result, SmartStableDiffusionGenerator.Result.failed)
        mock_llm.invoke.assert_called_once()
        self.simple_stable_diffusion_generator.execute.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_photo.assert_not_called()

    def test_execute_send_photo_failure(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined prompt")
        self.mock_di.chat_langchain_model.return_value = mock_llm

        self.simple_stable_diffusion_generator.execute.return_value = "http://example.com/image.png"
        self.mock_di.telegram_bot_sdk.send_photo.side_effect = Exception("Send photo error")

        generator = SmartStableDiffusionGenerator(
            self.raw_prompt,
            self.mock_configured_copywriter_tool,
            self.mock_configured_image_gen_tool,
            self.mock_di,
        )
        result = generator.execute()

        self.assertEqual(result, SmartStableDiffusionGenerator.Result.failed)
        mock_llm.invoke.assert_called_once()
        self.simple_stable_diffusion_generator.execute.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_photo.assert_called_once()

    def test_execute_non_ai_message(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "Not an AIMessage"
        self.mock_di.chat_langchain_model.return_value = mock_llm

        generator = SmartStableDiffusionGenerator(
            self.raw_prompt,
            self.mock_configured_copywriter_tool,
            self.mock_configured_image_gen_tool,
            self.mock_di,
        )
        result = generator.execute()

        self.assertEqual(result, SmartStableDiffusionGenerator.Result.failed)
        mock_llm.invoke.assert_called_once()
        # noinspection PyUnresolvedReferences
        self.mock_di.telegram_bot_sdk.send_photo.assert_not_called()
