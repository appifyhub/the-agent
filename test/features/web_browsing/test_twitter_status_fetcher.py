import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID

import requests
import requests_mock
from pydantic import SecretStr
from requests_mock import Mocker

from db.schema.tools_cache import ToolsCache
from di.di import DI
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.web_browsing.twitter_status_fetcher import TwitterStatusFetcher
from util.config import config


class TwitterStatusFetcherTest(unittest.TestCase):

    tweet_id: str
    api_url: str
    cache_entry: ToolsCache
    mock_di: DI
    mock_x_api_tool: ConfiguredTool
    mock_vision_tool: ConfiguredTool

    def setUp(self):
        config.web_timeout_s = 0
        self.tweet_id = "123456789"
        self.api_url = f"https://api.x.com/2/tweets/{self.tweet_id}"
        self.cache_entry = ToolsCache(
            key = "twitter-status-fetcher::123456789",
            value = "This is cached tweet content",
            expires_at = datetime.now() + timedelta(minutes = 5),
        )

        # Set up DI container
        self.mock_di = Mock(spec = DI)
        # noinspection PyPropertyAccess
        self.mock_di.tools_cache_crud = MagicMock()
        self.mock_di.tools_cache_crud.create_key.return_value = "test_cache_key"
        self.mock_di.tools_cache_crud.save.return_value = None
        self.mock_di.computer_vision_analyzer = MagicMock()

        # Mock invoker and chat for usage tracking
        mock_user = Mock()
        mock_user.id = UUID(int = 1)
        self.mock_di.invoker = mock_user

        mock_chat = Mock()
        mock_chat.chat_id = UUID(int = 2)
        self.mock_di.require_invoker_chat = MagicMock(return_value = mock_chat)

        # Mock tracked_http_get to return a mock that delegates to requests.get
        mock_http_client = MagicMock()
        mock_http_client.get = requests.get
        self.mock_di.tracked_http_get = MagicMock(return_value = mock_http_client)

        # Set up configured tools
        mock_x_tool = MagicMock()
        mock_x_tool.id = "x.api-v2-post.read"
        self.mock_x_api_tool = ConfiguredTool(
            definition = mock_x_tool,
            token = SecretStr("test_x_bearer_token"),
            purpose = MagicMock(),
            payer_id = UUID(int = 1),
            uses_credits = False,
        )

        mock_vision_tool = MagicMock()
        mock_vision_tool.id = "vision-tool-id"
        self.mock_vision_tool = ConfiguredTool(
            definition = mock_vision_tool,
            token = SecretStr("test_vision_token"),
            purpose = MagicMock(),
            payer_id = UUID(int = 1),
            uses_credits = False,
        )

    # noinspection PyUnusedLocal
    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_execute_cache_hit(self, m: Mocker, mock_sleep):
        self.mock_di.tools_cache_crud.get.return_value = self.cache_entry.model_dump()

        fetcher = TwitterStatusFetcher(
            tweet_id = "123456789",
            x_api_tool = self.mock_x_api_tool,
            vision_tool = self.mock_vision_tool,
            di = self.mock_di,
        )
        result = fetcher.execute()
        self.assertEqual(result, "This is cached tweet content")

    # noinspection PyUnusedLocal
    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_execute_cache_miss(self, m: Mocker, mock_sleep):
        self.mock_di.tools_cache_crud.get.return_value = None

        # Mock the X API v2 response
        m.get(
            self.api_url,
            json = {
                "data": {
                    "text": "Test tweet content",
                    "lang": "en",
                    "author_id": "123",
                },
                "includes": {
                    "users": [
                        {
                            "id": "123",
                            "username": "testuser",
                            "name": "Test User",
                            "description": "Test bio",
                        },
                    ],
                },
            },
        )

        fetcher = TwitterStatusFetcher(
            tweet_id = "123456789",
            x_api_tool = self.mock_x_api_tool,
            vision_tool = self.mock_vision_tool,
            di = self.mock_di,
        )
        result = fetcher.execute()
        self.assertIn("@testuser (Test User)", result)
        self.assertIn("Test tweet content", result)
        self.assertIn("@testuser's bio:", result)

    # noinspection PyUnusedLocal
    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_execute_api_error(self, m: Mocker, mock_sleep):
        self.mock_di.tools_cache_crud.get.return_value = None

        # Mock API error response
        m.get(self.api_url, status_code = 500)

        fetcher = TwitterStatusFetcher(
            tweet_id = "123456789",
            x_api_tool = self.mock_x_api_tool,
            vision_tool = self.mock_vision_tool,
            di = self.mock_di,
        )
        with self.assertRaises(requests.exceptions.HTTPError):
            fetcher.execute()

    # noinspection PyUnusedLocal
    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_api_call_parameters(self, m: Mocker, mock_sleep):
        self.mock_di.tools_cache_crud.get.return_value = None

        # Mock the X API v2 response
        m.get(
            self.api_url,
            json = {
                "data": {
                    "text": "Test tweet content",
                    "lang": "en",
                    "author_id": "123",
                },
                "includes": {
                    "users": [
                        {
                            "id": "123",
                            "username": "testuser",
                            "name": "Test User",
                            "description": "Test bio",
                        },
                    ],
                },
            },
        )

        fetcher = TwitterStatusFetcher(
            tweet_id = "123456789",
            x_api_tool = self.mock_x_api_tool,
            vision_tool = self.mock_vision_tool,
            di = self.mock_di,
        )
        fetcher.execute()

        # Verify API was called with correct parameters
        self.assertEqual(len(m.request_history), 1)
        request = m.request_history[0]
        self.assertEqual(request.method, "GET")
        self.assertIn("123456789", request.url)
        self.assertIn("Bearer test_x_bearer_token", request.headers.get("Authorization", ""))

    # noinspection PyUnusedLocal
    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_resolve_photo_contents(self, m: Mocker, mock_sleep):
        self.mock_di.tools_cache_crud.get.return_value = None

        # Mock computer vision analyzer
        mock_analyzer_instance = MagicMock()
        mock_analyzer_instance.execute.return_value = "Photo description"
        self.mock_di.computer_vision_analyzer.return_value = mock_analyzer_instance

        # Mock the X API v2 response with photo
        m.get(
            self.api_url,
            json = {
                "data": {
                    "text": "Test tweet content",
                    "lang": "en",
                    "author_id": "123",
                    "attachments": {
                        "media_keys": ["3_123"],
                    },
                },
                "includes": {
                    "users": [
                        {
                            "id": "123",
                            "username": "testuser",
                            "name": "Test User",
                            "description": "Test bio",
                        },
                    ],
                    "media": [
                        {
                            "media_key": "3_123",
                            "type": "photo",
                            "url": "https://example.com/photo.jpg",
                        },
                    ],
                },
            },
        )

        fetcher = TwitterStatusFetcher(
            tweet_id = "123456789",
            x_api_tool = self.mock_x_api_tool,
            vision_tool = self.mock_vision_tool,
            di = self.mock_di,
        )
        result = fetcher.execute()

        self.assertIn("Photo description", result)
        # noinspection PyUnresolvedReferences
        self.mock_di.computer_vision_analyzer.assert_called_once()

    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_format_tweet_content_handles_missing_data(self, m: Mocker, _):
        self.mock_di.tools_cache_crud.get.return_value = None

        # Mock X API v2 response with missing data
        m.get(
            self.api_url,
            json = {
                "data": {
                    "lang": "en",
                    "author_id": "123",
                },
                "includes": {
                    "users": [
                        {
                            "id": "123",
                            "username": "testuser",
                        },
                    ],
                },
            },
        )

        fetcher = TwitterStatusFetcher(
            tweet_id = "123456789",
            x_api_tool = self.mock_x_api_tool,
            vision_tool = self.mock_vision_tool,
            di = self.mock_di,
        )
        result = fetcher.execute()

        # Should handle missing data gracefully
        self.assertIn("@testuser (<Anonymous>)", result)
        self.assertIn("@testuser's bio: \"<No user bio>\"", result)
        self.assertIn("<No text posted>", result)
