import unittest
from time import sleep
from unittest.mock import Mock

from features.accounting.replicate_usage_tracking_decorator import (
    PredictionUsageTrackingDecorator,
    ReplicateUsageTrackingDecorator,
)
from features.accounting.usage_tracking_service import UsageTrackingService
from features.external_tools.external_tool import ExternalTool, ToolType


class ReplicateUsageTrackingDecoratorTest(unittest.TestCase):

    def setUp(self):
        self.mock_client = Mock()
        self.mock_tracking_service = Mock(spec = UsageTrackingService)
        self.tool_purpose = ToolType.images_edit
        self.external_tool = Mock(spec = ExternalTool)
        self.image_size = "512x512"

        self.decorator = ReplicateUsageTrackingDecorator(
            wrapped_client = self.mock_client,
            tracking_service = self.mock_tracking_service,
            external_tool = self.external_tool,
            tool_purpose = self.tool_purpose,
            image_size = self.image_size,
        )

    def test_predictions_property_returns_proxy(self):
        predictions = self.decorator.predictions

        self.assertIsNotNone(predictions)

    def test_create_returns_wrapped_prediction(self):
        mock_prediction = Mock()
        self.mock_client.predictions.create = Mock(return_value = mock_prediction)

        result = self.decorator.predictions.create(input = {"prompt": "test"})

        self.assertIsInstance(result, PredictionUsageTrackingDecorator)
        self.mock_client.predictions.create.assert_called_once_with(input = {"prompt": "test"})

    def test_other_predictions_methods_pass_through(self):
        self.mock_client.predictions.list = Mock(return_value = ["pred1", "pred2"])

        result = self.decorator.predictions.list()

        self.assertEqual(result, ["pred1", "pred2"])

    def test_client_attributes_pass_through(self):
        self.mock_client.some_attribute = "test_value"

        result = self.decorator.some_attribute

        self.assertEqual(result, "test_value")


class PredictionUsageTrackingDecoratorTest(unittest.TestCase):

    def setUp(self):
        self.mock_prediction = Mock()
        self.mock_tracking_service = Mock(spec = UsageTrackingService)
        self.tool_purpose = ToolType.images_edit
        self.external_tool = Mock(spec = ExternalTool)
        self.image_size = "512x512"

        self.decorator = PredictionUsageTrackingDecorator(
            wrapped_prediction = self.mock_prediction,
            tracking_service = self.mock_tracking_service,
            external_tool = self.external_tool,
            tool_purpose = self.tool_purpose,
            image_size = self.image_size,
        )

    def test_wait_tracks_usage(self):
        self.mock_prediction.metrics = Mock()
        self.mock_prediction.metrics.predict_time = 1.5
        self.mock_prediction.wait = Mock(return_value = "result")

        result = self.decorator.wait()

        self.assertEqual(result, "result")
        self.mock_tracking_service.track_image_model.assert_called_once()
        call_args = self.mock_tracking_service.track_image_model.call_args
        self.assertEqual(call_args.kwargs["tool"], self.external_tool)
        self.assertEqual(call_args.kwargs["tool_purpose"], self.tool_purpose)
        self.assertEqual(call_args.kwargs["image_size"], self.image_size)
        self.assertEqual(call_args.kwargs["remote_runtime_seconds"], 1.5)
        self.assertIsNotNone(call_args.kwargs["runtime_seconds"])
        self.assertGreater(call_args.kwargs["runtime_seconds"], 0)

    def test_wait_measures_runtime(self):
        self.mock_prediction.metrics = None

        def slow_wait():
            sleep(0.01)
            return "result"

        self.mock_prediction.wait = slow_wait

        self.decorator.wait()

        call_args = self.mock_tracking_service.track_image_model.call_args
        self.assertGreaterEqual(call_args.kwargs["runtime_seconds"], 0.01)

    def test_wait_with_no_metrics(self):
        self.mock_prediction.metrics = None
        self.mock_prediction.wait = Mock(return_value = "result")

        self.decorator.wait()

        call_args = self.mock_tracking_service.track_image_model.call_args
        self.assertIsNone(call_args.kwargs["remote_runtime_seconds"])

    def test_wait_tracks_only_once(self):
        self.mock_prediction.metrics = None
        self.mock_prediction.wait = Mock(return_value = "result")

        self.decorator.wait()
        self.decorator.wait()

        self.assertEqual(self.mock_tracking_service.track_image_model.call_count, 1)

    def test_wait_with_non_numeric_gpu_time(self):
        self.mock_prediction.metrics = Mock()
        self.mock_prediction.metrics.predict_time = "not_a_number"
        self.mock_prediction.wait = Mock(return_value = "result")

        self.decorator.wait()

        call_args = self.mock_tracking_service.track_image_model.call_args
        self.assertIsNone(call_args.kwargs["remote_runtime_seconds"])

    def test_prediction_attributes_pass_through(self):
        self.mock_prediction.status = "succeeded"

        result = self.decorator.status

        self.assertEqual(result, "succeeded")
