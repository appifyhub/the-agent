import unittest
from time import sleep
from unittest.mock import Mock

from google.genai.types import GenerateContentResponse

from features.accounting.decorators.google_ai_usage_tracking_decorator import GoogleAIUsageTrackingDecorator
from features.accounting.service.usage_tracking_service import UsageTrackingService
from features.external_tools.external_tool import ExternalTool, ToolType


class GoogleAIUsageTrackingDecoratorTest(unittest.TestCase):

    def setUp(self):
        self.mock_client = Mock()
        self.mock_tracking_service = Mock(spec = UsageTrackingService)
        self.tool_purpose = ToolType.images_gen
        self.external_tool = Mock(spec = ExternalTool)
        self.image_size = "1024x1024"

        self.decorator = GoogleAIUsageTrackingDecorator(
            wrapped_client = self.mock_client,
            tracking_service = self.mock_tracking_service,
            external_tool = self.external_tool,
            tool_purpose = self.tool_purpose,
            image_size = self.image_size,
        )

    def test_models_property_returns_proxy(self):
        models = self.decorator.models

        self.assertIsNotNone(models)

    def test_generate_content_tracks_usage(self):
        mock_response = Mock(spec = GenerateContentResponse)
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 200
        mock_response.usage_metadata.total_token_count = 300

        self.mock_client.models.generate_content = Mock(return_value = mock_response)

        result = self.decorator.models.generate_content(model = "test-model", contents = "test prompt")

        self.assertEqual(result, mock_response)
        self.mock_tracking_service.track_image_model.assert_called_once()
        call_args = self.mock_tracking_service.track_image_model.call_args
        self.assertEqual(call_args.kwargs["tool"], self.external_tool)
        self.assertEqual(call_args.kwargs["tool_purpose"], self.tool_purpose)
        self.assertEqual(call_args.kwargs["image_size"], self.image_size)
        self.assertEqual(call_args.kwargs["input_tokens"], 100)
        self.assertEqual(call_args.kwargs["output_tokens"], 200)
        self.assertEqual(call_args.kwargs["total_tokens"], 300)
        self.assertIsNotNone(call_args.kwargs["runtime_seconds"])
        self.assertGreater(call_args.kwargs["runtime_seconds"], 0)

    def test_generate_content_measures_runtime(self):
        mock_response = Mock(spec = GenerateContentResponse)
        mock_response.usage_metadata = None

        def slow_generate(*args, **kwargs):
            sleep(0.01)
            return mock_response

        self.mock_client.models.generate_content = slow_generate

        self.decorator.models.generate_content(model = "test-model", contents = "test prompt")

        call_args = self.mock_tracking_service.track_image_model.call_args
        self.assertGreaterEqual(call_args.kwargs["runtime_seconds"], 0.01)

    def test_generate_content_with_no_usage_metadata(self):
        mock_response = Mock(spec = GenerateContentResponse)
        mock_response.usage_metadata = None

        self.mock_client.models.generate_content = Mock(return_value = mock_response)

        self.decorator.models.generate_content(model = "test-model", contents = "test prompt")

        call_args = self.mock_tracking_service.track_image_model.call_args
        self.assertIsNone(call_args.kwargs["input_tokens"])
        self.assertIsNone(call_args.kwargs["output_tokens"])
        self.assertIsNone(call_args.kwargs["total_tokens"])

    def test_other_models_methods_pass_through(self):
        self.mock_client.models.list_models = Mock(return_value = ["model1", "model2"])

        result = self.decorator.models.list_models()

        self.assertEqual(result, ["model1", "model2"])
        self.mock_tracking_service.track_image_model.assert_not_called()

    def test_client_attributes_pass_through(self):
        self.mock_client.some_attribute = "test_value"

        result = self.decorator.some_attribute

        self.assertEqual(result, "test_value")

    def test_decorator_passes_arguments_correctly(self):
        mock_response = Mock(spec = GenerateContentResponse)
        mock_response.usage_metadata = None

        self.mock_client.models.generate_content = Mock(return_value = mock_response)

        self.decorator.models.generate_content(
            model = "test-model",
            contents = "test prompt",
            config = {"temperature": 0.7},
        )

        self.mock_client.models.generate_content.assert_called_once_with(
            model = "test-model",
            contents = "test prompt",
            config = {"temperature": 0.7},
        )
