import unittest
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from features.images.computer_vision_analyzer import ComputerVisionAnalyzer, KNOWN_IMAGE_FORMATS


class ComputerVisionAnalyzerTest(unittest.TestCase):

    def setUp(self):
        self.job_id = "test_job"
        self.image_mime_type = "image/jpeg"
        self.open_ai_api_key = "test_key"
        self.image_url = "https://example.com/image.jpg"
        self.image_b64 = "base64_encoded_image_data"

    def test_init_with_url(self):
        analyzer = ComputerVisionAnalyzer(
            self.job_id,
            self.image_mime_type,
            self.open_ai_api_key,
            image_url = self.image_url,
        )
        self.assertIsInstance(analyzer, ComputerVisionAnalyzer)

    def test_init_with_b64(self):
        analyzer = ComputerVisionAnalyzer(
            self.job_id,
            self.image_mime_type,
            self.open_ai_api_key,
            image_b64 = self.image_b64,
        )
        self.assertIsInstance(analyzer, ComputerVisionAnalyzer)

    def test_init_with_additional_context(self):
        additional_context = "This is an additional context"
        analyzer = ComputerVisionAnalyzer(
            self.job_id,
            self.image_mime_type,
            self.open_ai_api_key,
            image_url = self.image_url,
            additional_context = additional_context,
        )
        self.assertIsInstance(analyzer, ComputerVisionAnalyzer)

    def test_init_with_unsupported_image_format(self):
        with self.assertRaises(ValueError):
            ComputerVisionAnalyzer(self.job_id, "image/unsupported", self.open_ai_api_key, image_url = self.image_url)

    def test_init_with_both_url_and_b64(self):
        with self.assertRaises(ValueError):
            ComputerVisionAnalyzer(
                self.job_id,
                self.image_mime_type,
                self.open_ai_api_key,
                image_url = self.image_url,
                image_b64 = self.image_b64,
            )

    def test_init_with_neither_url_nor_b64(self):
        with self.assertRaises(ValueError):
            ComputerVisionAnalyzer(self.job_id, self.image_mime_type, self.open_ai_api_key)

    @patch("features.images.computer_vision_analyzer.ChatOpenAI")
    def test_execute_success(self, mock_chat_openai):
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content = "Analysis result")
        mock_chat_openai.return_value = mock_model
        analyzer = ComputerVisionAnalyzer(
            self.job_id,
            self.image_mime_type,
            self.open_ai_api_key,
            image_url = self.image_url,
        )
        result = analyzer.execute()
        self.assertEqual(result, "Analysis result")

    @patch("features.images.computer_vision_analyzer.ChatOpenAI")
    def test_execute_failure(self, mock_chat_openai):
        mock_model = MagicMock()
        mock_model.invoke.side_effect = Exception("API error")
        mock_chat_openai.return_value = mock_model
        analyzer = ComputerVisionAnalyzer(
            self.job_id,
            self.image_mime_type,
            self.open_ai_api_key,
            image_url = self.image_url,
        )
        result = analyzer.execute()
        self.assertEqual(result, None)

    @patch("features.images.computer_vision_analyzer.ChatOpenAI")
    def test_execute_non_ai_message(self, mock_chat_openai):
        mock_model = MagicMock()
        mock_model.invoke.return_value = "Not an AIMessage"
        mock_chat_openai.return_value = mock_model
        analyzer = ComputerVisionAnalyzer(
            self.job_id,
            self.image_mime_type,
            self.open_ai_api_key,
            image_url = self.image_url,
        )
        result = analyzer.execute()
        self.assertEqual(result, None)

    def test_known_image_formats(self):
        for ext, mime_type in KNOWN_IMAGE_FORMATS.items():
            analyzer = ComputerVisionAnalyzer(
                self.job_id,
                mime_type,
                self.open_ai_api_key,
                image_url = f"https://example.com/image.{ext}",
            )
            self.assertIsInstance(analyzer, ComputerVisionAnalyzer)
