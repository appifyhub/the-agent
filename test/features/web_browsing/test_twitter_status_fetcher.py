import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

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
    mock_twitter_api_tool: ConfiguredTool
    mock_vision_tool: ConfiguredTool
    mock_twitter_enterprise_tool: ConfiguredTool

    def setUp(self):
        config.web_timeout_s = 0
        config.rapid_api_twitter_token = SecretStr("test_twitter_api_token")
        self.tweet_id = "123456789"
        self.api_url = "https://twitter-api-v1-1-enterprise.p.rapidapi.com/base/apitools/tweetSimple"
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

        # Set up configured tools
        mock_twitter_tool = MagicMock()
        mock_twitter_tool.id = "twitter-api-v1-1-enterprise.p.rapidapi.com"
        self.mock_twitter_api_tool = (mock_twitter_tool, SecretStr("test_twitter_token"), MagicMock())

        mock_vision_tool = MagicMock()
        mock_vision_tool.id = "vision-tool-id"
        self.mock_vision_tool = (mock_vision_tool, SecretStr("test_vision_token"), MagicMock())

        mock_enterprise_tool = MagicMock()
        mock_enterprise_tool.id = "enterprise-tool-id"
        self.mock_twitter_enterprise_tool = (mock_enterprise_tool, SecretStr("test_enterprise_token"), MagicMock())

    # noinspection PyUnusedLocal
    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_execute_cache_hit(self, m: Mocker, mock_sleep):
        self.mock_di.tools_cache_crud.get.return_value = self.cache_entry.model_dump()

        fetcher = TwitterStatusFetcher(
            tweet_id = "123456789",
            twitter_api_tool = self.mock_twitter_api_tool,
            vision_tool = self.mock_vision_tool,
            twitter_enterprise_tool = self.mock_twitter_enterprise_tool,
            di = self.mock_di,
        )
        result = fetcher.execute()
        self.assertEqual(result, "This is cached tweet content")

    # noinspection PyUnusedLocal
    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_execute_cache_miss(self, m: Mocker, mock_sleep):
        self.mock_di.tools_cache_crud.get.return_value = None

        # Mock the API response
        m.get(
            self.api_url,
            json = {
                "data": {
                    "data": {
                        "tweetResult": {
                            "result": {
                                "core": {
                                    "user_results": {
                                        "result": {
                                            "legacy": {
                                                "name": "Test User",
                                                "screen_name": "testuser",
                                                "description": "Test bio",
                                            },
                                        },
                                    },
                                },
                                "legacy": {"full_text": "Test tweet content", "lang": "en"},
                            },
                        },
                    },
                },
            },
        )

        fetcher = TwitterStatusFetcher(
            tweet_id = "123456789",
            twitter_api_tool = self.mock_twitter_api_tool,
            vision_tool = self.mock_vision_tool,
            twitter_enterprise_tool = self.mock_twitter_enterprise_tool,
            di = self.mock_di,
        )
        result = fetcher.execute()
        self.assertIn("@testuser · Test User", result)
        self.assertIn("Test tweet content", result)

    # noinspection PyUnusedLocal
    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_execute_api_error(self, m: Mocker, mock_sleep):
        self.mock_di.tools_cache_crud.get.return_value = None

        # Mock API error response
        m.get(self.api_url, status_code = 500)

        fetcher = TwitterStatusFetcher(
            tweet_id = "123456789",
            twitter_api_tool = self.mock_twitter_api_tool,
            vision_tool = self.mock_vision_tool,
            twitter_enterprise_tool = self.mock_twitter_enterprise_tool,
            di = self.mock_di,
        )
        with self.assertRaises(requests.exceptions.HTTPError):
            fetcher.execute()

    # noinspection PyUnusedLocal
    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_api_call_parameters(self, m: Mocker, mock_sleep):
        self.mock_di.tools_cache_crud.get.return_value = None

        # Mock the API response
        m.get(
            self.api_url,
            json = {
                "data": {
                    "data": {
                        "tweetResult": {
                            "result": {
                                "core": {
                                    "user_results": {
                                        "result": {
                                            "legacy": {
                                                "name": "Test User",
                                                "screen_name": "testuser",
                                                "description": "Test bio",
                                            },
                                        },
                                    },
                                },
                                "legacy": {"full_text": "Test tweet content", "lang": "en"},
                            },
                        },
                    },
                },
            },
        )

        fetcher = TwitterStatusFetcher(
            tweet_id = "123456789",
            twitter_api_tool = self.mock_twitter_api_tool,
            vision_tool = self.mock_vision_tool,
            twitter_enterprise_tool = self.mock_twitter_enterprise_tool,
            di = self.mock_di,
        )
        fetcher.execute()

        # Verify API was called with correct parameters
        self.assertEqual(len(m.request_history), 1)
        request = m.request_history[0]
        self.assertEqual(request.method, "GET")
        self.assertIn("123456789", request.url)

    # noinspection PyUnusedLocal
    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_resolve_photo_contents(self, m: Mocker, mock_sleep):
        self.mock_di.tools_cache_crud.get.return_value = None

        # Mock computer vision analyzer
        mock_analyzer_instance = MagicMock()
        mock_analyzer_instance.execute.return_value = "Photo description"
        self.mock_di.computer_vision_analyzer.return_value = mock_analyzer_instance

        # Mock the API response with photo
        m.get(
            self.api_url,
            json = {
                "data": {
                    "data": {
                        "tweetResult": {
                            "result": {
                                "core": {
                                    "user_results": {
                                        "result": {
                                            "legacy": {
                                                "name": "Test User",
                                                "screen_name": "testuser",
                                                "description": "Test bio",
                                            },
                                        },
                                    },
                                },
                                "legacy": {
                                    "full_text": "Test tweet content",
                                    "lang": "en",
                                    "extended_entities": {
                                        "media": [
                                            {
                                                "type": "photo",
                                                "media_url_https": "https://example.com/photo.jpg",
                                            },
                                        ],
                                    },
                                },
                            },
                        },
                    },
                },
            },
        )

        fetcher = TwitterStatusFetcher(
            tweet_id = "123456789",
            twitter_api_tool = self.mock_twitter_api_tool,
            vision_tool = self.mock_vision_tool,
            twitter_enterprise_tool = self.mock_twitter_enterprise_tool,
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

        # Mock API response with missing data
        m.get(
            self.api_url,
            json = {
                "data": {
                    "data": {
                        "tweetResult": {
                            "result": {
                                "core": {
                                    "user_results": {
                                        "result": {
                                            "legacy": {
                                                "screen_name": "testuser",
                                            },
                                        },
                                    },
                                },
                                "legacy": {
                                    "lang": "en",
                                },
                            },
                        },
                    },
                },
            },
        )

        fetcher = TwitterStatusFetcher(
            tweet_id = "123456789",
            twitter_api_tool = self.mock_twitter_api_tool,
            vision_tool = self.mock_vision_tool,
            twitter_enterprise_tool = self.mock_twitter_enterprise_tool,
            di = self.mock_di,
        )
        result = fetcher.execute()

        # Should handle missing data gracefully
        self.assertIn("@testuser · <Anonymous>", result)
        self.assertIn("Bio: \"<No bio>\"", result)
        self.assertIn("<This tweet has no text>", result)
