import unittest
from time import sleep
from unittest.mock import Mock

from langchain_core.messages import AIMessage

from features.accounting.chat_model_usage_tracking_decorator import (
    ChatModelUsageTrackingDecorator,
    RunnableUsageTrackingDecorator,
)
from features.accounting.usage_tracking_service import UsageTrackingService
from features.external_tools.external_tool import ExternalTool, ToolType


class ChatModelUsageTrackingDecoratorTest(unittest.TestCase):

    def setUp(self):
        self.mock_model = Mock()
        self.mock_tracking_service = Mock(spec = UsageTrackingService)
        self.tool_purpose = ToolType.chat
        self.external_tool = Mock(spec = ExternalTool)

        self.decorator = ChatModelUsageTrackingDecorator(
            wrapped_model = self.mock_model,
            tracking_service = self.mock_tracking_service,
            external_tool = self.external_tool,
            tool_purpose = self.tool_purpose,
        )

    def test_invoke_tracks_usage(self):
        mock_response = Mock(spec = AIMessage)
        mock_response.response_metadata = {
            "usage": {
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300,
            },
        }
        mock_response.usage_metadata = None

        self.mock_model.invoke = Mock(return_value = mock_response)

        result = self.decorator.invoke("test input")

        self.assertEqual(result, mock_response)
        self.mock_tracking_service.track_text_model.assert_called_once()
        call_args = self.mock_tracking_service.track_text_model.call_args
        self.assertEqual(call_args.kwargs["tool"], self.external_tool)
        self.assertEqual(call_args.kwargs["tool_purpose"], self.tool_purpose)
        self.assertEqual(call_args.kwargs["input_tokens"], 100)
        self.assertEqual(call_args.kwargs["output_tokens"], 200)
        self.assertEqual(call_args.kwargs["total_tokens"], 300)
        self.assertIsNotNone(call_args.kwargs["runtime_seconds"])
        self.assertGreater(call_args.kwargs["runtime_seconds"], 0)

    def test_invoke_measures_runtime(self):
        mock_response = Mock(spec = AIMessage)
        mock_response.response_metadata = {}
        mock_response.usage_metadata = None

        def slow_invoke(*args, **kwargs):
            sleep(0.01)
            return mock_response

        self.mock_model.invoke = slow_invoke

        self.decorator.invoke("test input")

        call_args = self.mock_tracking_service.track_text_model.call_args
        self.assertGreaterEqual(call_args.kwargs["runtime_seconds"], 0.01)

    def test_invoke_passes_arguments_correctly(self):
        mock_response = Mock(spec = AIMessage)
        mock_response.response_metadata = {}
        mock_response.usage_metadata = None

        self.mock_model.invoke = Mock(return_value = mock_response)

        self.decorator.invoke("test input", {"temperature": 0.7}, stream = False)

        self.mock_model.invoke.assert_called_once_with("test input", {"temperature": 0.7}, stream = False)

    def test_bind_tools_returns_wrapped_runnable(self):
        mock_runnable = Mock()
        self.mock_model.bind_tools = Mock(return_value = mock_runnable)

        result = self.decorator.bind_tools(["tool1", "tool2"])

        self.assertIsInstance(result, RunnableUsageTrackingDecorator)
        self.mock_model.bind_tools.assert_called_once_with(["tool1", "tool2"])

    def test_generate_delegates_to_wrapped_model(self):
        self.mock_model._generate = Mock(return_value = "generated")

        result = self.decorator._generate("input")

        self.assertEqual(result, "generated")
        self.mock_model._generate.assert_called_once_with("input")

    def test_llm_type_delegates_to_wrapped_model(self):
        self.mock_model._llm_type = "test_llm_type"

        result = self.decorator._llm_type

        self.assertEqual(result, "test_llm_type")


class RunnableUsageTrackingDecoratorTest(unittest.TestCase):

    def setUp(self):
        self.mock_runnable = Mock()
        self.mock_tracking_service = Mock(spec = UsageTrackingService)
        self.tool_purpose = ToolType.chat
        self.external_tool = Mock(spec = ExternalTool)

        self.decorator = RunnableUsageTrackingDecorator(
            wrapped_runnable = self.mock_runnable,
            tracking_service = self.mock_tracking_service,
            external_tool = self.external_tool,
            tool_purpose = self.tool_purpose,
        )

    def test_invoke_tracks_usage(self):
        mock_response = Mock(spec = AIMessage)
        mock_response.response_metadata = {
            "usage": {
                "input_tokens": 50,
                "output_tokens": 100,
                "total_tokens": 150,
            },
        }
        mock_response.usage_metadata = None

        self.mock_runnable.invoke = Mock(return_value = mock_response)

        result = self.decorator.invoke("test input")

        self.assertEqual(result, mock_response)
        self.mock_tracking_service.track_text_model.assert_called_once()
        call_args = self.mock_tracking_service.track_text_model.call_args
        self.assertEqual(call_args.kwargs["tool"], self.external_tool)
        self.assertEqual(call_args.kwargs["tool_purpose"], self.tool_purpose)
        self.assertEqual(call_args.kwargs["input_tokens"], 50)
        self.assertEqual(call_args.kwargs["output_tokens"], 100)
        self.assertEqual(call_args.kwargs["total_tokens"], 150)

    def test_invoke_measures_runtime(self):
        mock_response = Mock(spec = AIMessage)
        mock_response.response_metadata = {}
        mock_response.usage_metadata = None

        def slow_invoke(*args, **kwargs):
            sleep(0.01)
            return mock_response

        self.mock_runnable.invoke = slow_invoke

        self.decorator.invoke("test input")

        call_args = self.mock_tracking_service.track_text_model.call_args
        self.assertGreaterEqual(call_args.kwargs["runtime_seconds"], 0.01)
