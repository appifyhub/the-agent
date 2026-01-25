import unittest
from time import sleep
from unittest.mock import Mock

import requests

from features.accounting.decorators.http_usage_tracking_decorator import HTTPUsageTrackingDecorator
from features.accounting.service.usage_tracking_service import UsageTrackingService
from features.external_tools.external_tool import ExternalTool, ToolType


class HTTPUsageTrackingDecoratorTest(unittest.TestCase):

    def setUp(self):
        self.mock_tracking_service = Mock(spec = UsageTrackingService)
        self.tool_purpose = ToolType.api_twitter
        self.external_tool = Mock(spec = ExternalTool)

        self.decorator = HTTPUsageTrackingDecorator(
            tracking_service = self.mock_tracking_service,
            external_tool = self.external_tool,
            tool_purpose = self.tool_purpose,
        )

    def test_get_tracks_api_call(self):
        mock_response = Mock(spec = requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}

        with unittest.mock.patch("requests.get", return_value = mock_response) as mock_get:
            result = self.decorator.get("https://api.example.com/test", headers = {"X-API-Key": "test"})

        self.assertEqual(result, mock_response)
        mock_get.assert_called_once_with("https://api.example.com/test", headers = {"X-API-Key": "test"})
        self.mock_tracking_service.track_api_call.assert_called_once()
        call_args = self.mock_tracking_service.track_api_call.call_args
        self.assertEqual(call_args.kwargs["tool"], self.external_tool)
        self.assertEqual(call_args.kwargs["tool_purpose"], self.tool_purpose)
        self.assertIsNotNone(call_args.kwargs["runtime_seconds"])
        self.assertGreater(call_args.kwargs["runtime_seconds"], 0)

    def test_get_measures_runtime(self):
        mock_response = Mock(spec = requests.Response)

        def slow_get(*args, **kwargs):
            sleep(0.01)
            return mock_response

        with unittest.mock.patch("requests.get", side_effect = slow_get):
            self.decorator.get("https://api.example.com/test")

        call_args = self.mock_tracking_service.track_api_call.call_args
        self.assertGreaterEqual(call_args.kwargs["runtime_seconds"], 0.01)

    def test_get_passes_kwargs_correctly(self):
        mock_response = Mock(spec = requests.Response)

        with unittest.mock.patch("requests.get", return_value = mock_response) as mock_get:
            self.decorator.get(
                "https://api.example.com/test",
                headers = {"X-API-Key": "test"},
                params = {"id": "123"},
                timeout = 30,
            )

        mock_get.assert_called_once_with(
            "https://api.example.com/test",
            headers = {"X-API-Key": "test"},
            params = {"id": "123"},
            timeout = 30,
        )

    def test_get_propagates_exceptions(self):
        with unittest.mock.patch("requests.get", side_effect = requests.exceptions.HTTPError("404")):
            with self.assertRaises(requests.exceptions.HTTPError):
                self.decorator.get("https://api.example.com/test")

        # Exception is raised before tracking, so it should not have been called
        self.mock_tracking_service.track_api_call.assert_not_called()
