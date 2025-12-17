import unittest
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from db.model.chat_config import ChatConfigDB
from di.di import DI
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.images.smart_stable_diffusion_generator import SmartStableDiffusionGenerator
from features.integrations.platform_bot_sdk import PlatformBotSDK


class SmartStableDiffusionGeneratorTest(unittest.TestCase):

    raw_prompt: str
    mock_di: DI
    mock_configured_copywriter_tool: ConfiguredTool
    mock_configured_image_gen_tool: ConfiguredTool

    def setUp(self):
        self.raw_prompt = "Generate a beautiful landscape"

        # Mock DI
        self.mock_di = MagicMock()
        mock_chat = MagicMock()
        mock_chat.external_id = "1"
        mock_chat.chat_type = ChatConfigDB.ChatType.telegram
        mock_chat.media_mode = ChatConfigDB.MediaMode.all  # Default to 'all' mode to match old behavior
        self.mock_di.require_invoker_chat = MagicMock(return_value = mock_chat)
        self.mock_di.invoker_chat_type = ChatConfigDB.ChatType.telegram
        self.mock_di.require_invoker_chat_type = MagicMock(return_value = ChatConfigDB.ChatType.telegram)
        # noinspection PyPropertyAccess
        self.mock_platform_sdk = MagicMock(spec = PlatformBotSDK)
        self.mock_di.platform_bot_sdk = MagicMock(return_value = self.mock_platform_sdk)
        self.mock_platform_sdk.send_photo.return_value = {"result": {"message_id": 123}}
        self.mock_platform_sdk.send_document.return_value = {"result": {"message_id": 124}}

        # Mock text_stable_diffusion_generator method
        self.simple_stable_diffusion_generator = MagicMock()
        # Mock the error property - default to no error
        self.simple_stable_diffusion_generator.error = None
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
        self.simple_stable_diffusion_generator.error = None

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
        self.mock_platform_sdk.smart_send_photo.assert_called_once_with(
            media_mode = ChatConfigDB.MediaMode.all,
            chat_id = 1,
            photo_url = "http://example.com/image.png",
            caption = "📸",
            thumbnail = "http://example.com/image.png",
        )

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
        self.simple_stable_diffusion_generator.execute.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_platform_sdk.send_document.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_platform_sdk.send_photo.assert_not_called()

    def test_execute_image_generation_failure(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined prompt")
        self.mock_di.chat_langchain_model.return_value = mock_llm

        self.simple_stable_diffusion_generator.execute.return_value = None
        # Set an error on the image generator
        self.simple_stable_diffusion_generator.error = "Image generation failed"

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
        self.mock_platform_sdk.send_document.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_platform_sdk.send_photo.assert_not_called()

    def test_execute_send_photo_failure(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined prompt")
        self.mock_di.chat_langchain_model.return_value = mock_llm

        self.simple_stable_diffusion_generator.execute.return_value = "http://example.com/image.png"
        # Make sure no error is set on the image generator
        self.simple_stable_diffusion_generator.error = None
        self.mock_platform_sdk.smart_send_photo.side_effect = Exception("Send photo error")

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
        self.mock_platform_sdk.smart_send_photo.assert_called_once()

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
        self.mock_platform_sdk.send_document.assert_not_called()
        # noinspection PyUnresolvedReferences
        self.mock_platform_sdk.send_photo.assert_not_called()
