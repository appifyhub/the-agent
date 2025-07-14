import unittest
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from features.chat.chat_image_gen_service import ChatImageGenService
from features.external_tools.tool_choice_resolver import ConfiguredTool


class ChatImageGenServiceTest(unittest.TestCase):
    raw_prompt: str
    mock_di: MagicMock
    mock_configured_copywriter_tool: ConfiguredTool
    mock_configured_image_gen_tool: ConfiguredTool

    def setUp(self):
        self.raw_prompt = "Generate a beautiful landscape"

        # Mock DI
        self.mock_di = MagicMock()
        self.mock_di.invoker_chat.chat_id = "test_chat_id"
        self.mock_di.telegram_bot_sdk.send_photo.return_value = {"result": {"message_id": 123}}

        # Mock text_stable_diffusion_generator method
        self.mock_text_stable_diffusion_generator = MagicMock()
        self.mock_di.text_stable_diffusion_generator.return_value = self.mock_text_stable_diffusion_generator

        # Mock configured tools
        self.mock_configured_copywriter_tool = MagicMock(spec = ConfiguredTool)
        self.mock_configured_image_gen_tool = MagicMock(spec = ConfiguredTool)

    @patch("features.chat.chat_image_gen_service.langchain_creator.create")
    def test_init_success(self, mock_langchain_create):
        mock_langchain_create.return_value = MagicMock()

        service = ChatImageGenService(
            self.raw_prompt,
            self.mock_configured_copywriter_tool,
            self.mock_configured_image_gen_tool,
            self.mock_di,
        )
        self.assertIsInstance(service, ChatImageGenService)

    @patch("features.chat.chat_image_gen_service.langchain_creator.create")
    def test_execute_success(self, mock_langchain_create):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined prompt")
        mock_langchain_create.return_value = mock_llm

        self.mock_text_stable_diffusion_generator.execute.return_value = "http://example.com/image.png"

        service = ChatImageGenService(
            self.raw_prompt,
            self.mock_configured_copywriter_tool,
            self.mock_configured_image_gen_tool,
            self.mock_di,
        )
        result = service.execute()

        self.assertEqual(result, ChatImageGenService.Result.success)
        mock_llm.invoke.assert_called_once()
        self.mock_text_stable_diffusion_generator.execute.assert_called_once()
        self.mock_di.telegram_bot_sdk.send_photo.assert_called_once_with("test_chat_id", "http://example.com/image.png")

    @patch("features.chat.chat_image_gen_service.langchain_creator.create")
    def test_execute_llm_failure(self, mock_langchain_create):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM error")
        mock_langchain_create.return_value = mock_llm

        service = ChatImageGenService(
            self.raw_prompt,
            self.mock_configured_copywriter_tool,
            self.mock_configured_image_gen_tool,
            self.mock_di,
        )
        result = service.execute()

        self.assertEqual(result, ChatImageGenService.Result.failed)
        mock_llm.invoke.assert_called_once()
        self.mock_di.telegram_bot_sdk.send_photo.assert_not_called()

    @patch("features.chat.chat_image_gen_service.langchain_creator.create")
    def test_execute_image_generation_failure(self, mock_langchain_create):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined prompt")
        mock_langchain_create.return_value = mock_llm

        self.mock_text_stable_diffusion_generator.execute.return_value = None

        service = ChatImageGenService(
            self.raw_prompt,
            self.mock_configured_copywriter_tool,
            self.mock_configured_image_gen_tool,
            self.mock_di,
        )
        result = service.execute()

        self.assertEqual(result, ChatImageGenService.Result.failed)
        mock_llm.invoke.assert_called_once()
        self.mock_text_stable_diffusion_generator.execute.assert_called_once()
        self.mock_di.telegram_bot_sdk.send_photo.assert_not_called()

    @patch("features.chat.chat_image_gen_service.langchain_creator.create")
    def test_execute_send_photo_failure(self, mock_langchain_create):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content = "Refined prompt")
        mock_langchain_create.return_value = mock_llm

        self.mock_text_stable_diffusion_generator.execute.return_value = "http://example.com/image.png"
        self.mock_di.telegram_bot_sdk.send_photo.side_effect = Exception("Send photo error")

        service = ChatImageGenService(
            self.raw_prompt,
            self.mock_configured_copywriter_tool,
            self.mock_configured_image_gen_tool,
            self.mock_di,
        )
        result = service.execute()

        self.assertEqual(result, ChatImageGenService.Result.failed)
        mock_llm.invoke.assert_called_once()
        self.mock_text_stable_diffusion_generator.execute.assert_called_once()
        self.mock_di.telegram_bot_sdk.send_photo.assert_called_once()

    @patch("features.chat.chat_image_gen_service.langchain_creator.create")
    def test_execute_non_ai_message(self, mock_langchain_create):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "Not an AIMessage"
        mock_langchain_create.return_value = mock_llm

        service = ChatImageGenService(
            self.raw_prompt,
            self.mock_configured_copywriter_tool,
            self.mock_configured_image_gen_tool,
            self.mock_di,
        )
        result = service.execute()

        self.assertEqual(result, ChatImageGenService.Result.failed)
        mock_llm.invoke.assert_called_once()
        self.mock_di.telegram_bot_sdk.send_photo.assert_not_called()
