import unittest
from time import sleep
from unittest.mock import Mock
from uuid import UUID

from features.accounting.spending.spending_service import SpendingService
from features.accounting.usage.decorators.x_ai_usage_tracking_decorator import XAIUsageTrackingDecorator
from features.accounting.usage.usage_record import UsageRecord
from features.accounting.usage.usage_tracking_service import UsageTrackingService
from features.external_tools.configured_tool import ConfiguredTool
from features.external_tools.external_tool import ExternalTool, ToolType


class XAIUsageTrackingDecoratorTest(unittest.TestCase):

    def setUp(self):
        self.mock_client = Mock()
        self.mock_tracking_service = Mock(spec = UsageTrackingService)
        self.mock_tracking_service.track_image_model = Mock(
            return_value = Mock(spec = UsageRecord, total_cost_credits = 2.0),
        )
        self.mock_spending_service = Mock(spec = SpendingService)
        self.tool_purpose = ToolType.images_gen
        self.external_tool = Mock(spec = ExternalTool)
        self.external_tool.id = "grok-imagine-image"
        self.image_size = "1k"

        self.mock_configured_tool = Mock(spec = ConfiguredTool)
        self.mock_configured_tool.definition = self.external_tool
        self.mock_configured_tool.purpose = self.tool_purpose
        self.mock_configured_tool.payer_id = UUID(int = 1)
        self.mock_configured_tool.uses_credits = False

        self.decorator = XAIUsageTrackingDecorator(
            wrapped_client = self.mock_client,
            tracking_service = self.mock_tracking_service,
            spending_service = self.mock_spending_service,
            configured_tool = self.mock_configured_tool,
            output_image_sizes = [self.image_size],
        )

    def test_image_property_returns_proxy(self):
        image = self.decorator.image

        self.assertIsNotNone(image)

    def test_sample_tracks_usage_by_image_size(self):
        mock_response = Mock()
        self.mock_client.image.sample = Mock(return_value = mock_response)

        result = self.decorator.image.sample(
            prompt = "test prompt",
            model = "grok-imagine-image",
            image_format = "base64",
        )

        self.assertEqual(result, mock_response)
        self.mock_tracking_service.track_image_model.assert_called_once()
        call_args = self.mock_tracking_service.track_image_model.call_args
        self.assertEqual(call_args.kwargs["tool"], self.external_tool)
        self.assertEqual(call_args.kwargs["tool_purpose"], self.tool_purpose)
        self.assertEqual(call_args.kwargs["output_image_sizes"], [self.image_size])
        self.assertIsNone(call_args.kwargs.get("input_tokens"))
        self.assertIsNone(call_args.kwargs.get("output_tokens"))
        self.assertIsNotNone(call_args.kwargs["runtime_seconds"])
        self.assertGreater(call_args.kwargs["runtime_seconds"], 0)
        self.assertEqual(call_args.kwargs["uses_credits"], False)

    def test_sample_deducts_credits(self):
        mock_response = Mock()
        self.mock_client.image.sample = Mock(return_value = mock_response)

        self.decorator.image.sample(prompt = "test", model = "grok-imagine-image")

        self.mock_spending_service.deduct.assert_called_once_with(self.mock_configured_tool, 2.0)

    def test_sample_measures_runtime(self):
        def slow_sample(*args, **kwargs):
            sleep(0.01)
            return Mock()

        self.mock_client.image.sample = slow_sample

        self.decorator.image.sample(prompt = "test", model = "grok-imagine-image")

        call_args = self.mock_tracking_service.track_image_model.call_args
        self.assertGreaterEqual(call_args.kwargs["runtime_seconds"], 0.01)

    def test_sample_calls_validate_pre_flight(self):
        self.mock_client.image.sample = Mock(return_value = Mock())

        self.decorator.image.sample(prompt = "test", model = "grok-imagine-image")

        self.mock_spending_service.validate_pre_flight.assert_called_once_with(
            self.mock_configured_tool,
            input_image_sizes = None,
            output_image_sizes = [self.image_size],
        )

    def test_sample_failure_tracks_without_deduction(self):
        self.mock_client.image.sample = Mock(side_effect = RuntimeError("API error"))

        with self.assertRaises(RuntimeError):
            self.decorator.image.sample(prompt = "test", model = "grok-imagine-image")

        self.mock_tracking_service.track_image_model.assert_called_once()
        call_args = self.mock_tracking_service.track_image_model.call_args
        self.assertTrue(call_args.kwargs["is_failed"])
        self.mock_spending_service.deduct.assert_not_called()

    def test_other_image_methods_pass_through(self):
        self.mock_client.image.list_models = Mock(return_value = ["model1"])

        result = self.decorator.image.list_models()

        self.assertEqual(result, ["model1"])
        self.mock_tracking_service.track_image_model.assert_not_called()

    def test_client_attributes_pass_through(self):
        self.mock_client.some_attribute = "test_value"

        result = self.decorator.some_attribute

        self.assertEqual(result, "test_value")

    def test_sample_passes_arguments_correctly(self):
        self.mock_client.image.sample = Mock(return_value = Mock())

        self.decorator.image.sample(
            prompt = "a robot",
            model = "grok-imagine-image",
            aspect_ratio = "16:9",
            resolution = "2k",
            image_format = "base64",
        )

        self.mock_client.image.sample.assert_called_once_with(
            prompt = "a robot",
            model = "grok-imagine-image",
            aspect_ratio = "16:9",
            resolution = "2k",
            image_format = "base64",
        )

    def test_no_output_image_sizes(self):
        decorator = XAIUsageTrackingDecorator(
            wrapped_client = self.mock_client,
            tracking_service = self.mock_tracking_service,
            spending_service = self.mock_spending_service,
            configured_tool = self.mock_configured_tool,
        )
        self.mock_client.image.sample = Mock(return_value = Mock())

        decorator.image.sample(prompt = "test", model = "grok-imagine-image")

        call_args = self.mock_tracking_service.track_image_model.call_args
        self.assertIsNone(call_args.kwargs["output_image_sizes"])
