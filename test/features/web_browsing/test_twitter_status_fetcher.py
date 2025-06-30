import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

import requests
import requests_mock
from pydantic import SecretStr
from requests_mock import Mocker

from db.crud.tools_cache import ToolsCacheCRUD
from db.schema.tools_cache import ToolsCache
from features.web_browsing.twitter_status_fetcher import TwitterStatusFetcher
from util.config import config


class TwitterStatusFetcherTest(unittest.TestCase):
    tweet_id: str
    api_url: str
    cache_entry: ToolsCache
    mock_cache_crud: ToolsCacheCRUD
    mock_user_dao: MagicMock
    mock_chat_config_dao: MagicMock
    mock_sponsorship_dao: MagicMock
    mock_telegram_bot_sdk: MagicMock
    mock_user: MagicMock

    def setUp(self):
        config.web_timeout_s = 0
        config.rapid_api_twitter_token = "test_twitter_api_token"
        self.tweet_id = "123456789"
        self.api_url = "https://twitter-api-v1-1-enterprise.p.rapidapi.com/base/apitools/tweetSimple"
        self.cache_entry = ToolsCache(
            key = "twitter-status-fetcher::123456789",
            value = "This is cached tweet content",
            expires_at = datetime.now() + timedelta(minutes = 5),
        )
        self.mock_cache_crud = MagicMock()
        self.mock_cache_crud.create_key.return_value = "test_cache_key"
        self.mock_cache_crud.save.return_value = None
        self.mock_user_dao = MagicMock()
        self.mock_chat_config_dao = MagicMock()
        self.mock_sponsorship_dao = MagicMock()
        self.mock_telegram_bot_sdk = MagicMock()

        # Mock user
        self.mock_user = MagicMock()
        self.mock_user.id = UUID("12345678-1234-5678-1234-567812345678")

    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.AuthorizationService")
    @patch("features.web_browsing.twitter_status_fetcher.AccessTokenResolver")
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_execute_cache_hit(self, m: Mocker, mock_sleep, mock_token_resolver, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user
        mock_token_resolver.return_value.require_access_token_for_tool.return_value = SecretStr("test_token")

        self.mock_cache_crud.get.return_value = self.cache_entry.model_dump()
        fetcher = TwitterStatusFetcher(
            "123456789",
            self.mock_user,
            self.mock_cache_crud,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        result = fetcher.execute()
        self.assertEqual(result, "This is cached tweet content")

    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.AuthorizationService")
    @patch("features.web_browsing.twitter_status_fetcher.AccessTokenResolver")
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_execute_cache_miss(self, m, mock_sleep, mock_token_resolver, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user
        mock_token_resolver.return_value.get_access_token_for_tool.return_value = SecretStr("test_token")
        mock_token_resolver.return_value.require_access_token_for_tool.return_value = SecretStr("test_token")

        self.mock_cache_crud.get.return_value = None
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
            "123456789",
            self.mock_user,
            self.mock_cache_crud,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        result = fetcher.execute()
        self.assertIn("@testuser · Test User", result)
        self.assertIn("Test tweet content", result)

    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.AuthorizationService")
    @patch("features.web_browsing.twitter_status_fetcher.AccessTokenResolver")
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_execute_api_error(self, m, mock_sleep, mock_token_resolver, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user
        mock_token_resolver.return_value.require_access_token_for_tool.return_value = SecretStr("test_token")

        self.mock_cache_crud.get.return_value = None
        params = {
            "resFormat": "json",
            "id": "123456789",
            "apiKey": config.rapid_api_twitter_token,
            "cursor": "-1",
        }
        full_url = requests.Request("GET", self.api_url, params = params).prepare().url
        m.get(full_url, status_code = 500)
        fetcher = TwitterStatusFetcher(
            "123456789",
            self.mock_user,
            self.mock_cache_crud,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        with self.assertRaises(Exception):
            fetcher.execute()

    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.AuthorizationService")
    @patch("features.web_browsing.twitter_status_fetcher.AccessTokenResolver")
    @patch("features.web_browsing.twitter_status_fetcher.sleep", return_value = None)
    def test_api_call_parameters(self, m, mock_sleep, mock_token_resolver, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user
        mock_token_resolver.return_value.get_access_token_for_tool.return_value = SecretStr("test_token")
        mock_token_resolver.return_value.require_access_token_for_tool.return_value = SecretStr("test_token")

        self.mock_cache_crud.get.return_value = None

        m.get(
            self.api_url,
            json = {
                "data": {
                    "data": {
                        "tweetResult": {
                            "result": {"core": {"user_results": {"result": {"legacy": {}}}}, "legacy": {}},
                        },
                    },
                },
            },
        )
        fetcher = TwitterStatusFetcher(
            "123456789",
            self.mock_user,
            self.mock_cache_crud,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        fetcher.execute()

        # Check that the API was called with the correct parameters
        self.assertEqual(len(m.request_history), 1)
        request = m.request_history[0]
        self.assertIn("id=123456789", request.url)
        self.assertIn("resFormat=json", request.url)

    @requests_mock.Mocker()
    @patch("features.web_browsing.twitter_status_fetcher.AuthorizationService")
    @patch("features.web_browsing.twitter_status_fetcher.AccessTokenResolver")
    @patch("features.web_browsing.twitter_status_fetcher.ComputerVisionAnalyzer")
    def test_resolve_photo_contents(self, m, mock_analyzer, mock_token_resolver, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user
        mock_token_resolver.return_value.require_access_token_for_tool.return_value = SecretStr("test_token")

        # Mock the analyzer's execute method to return a fixed description
        mock_analyzer.return_value.execute.return_value = "A beautiful landscape."

        fetcher = TwitterStatusFetcher(
            "123456789",
            self.mock_user,
            self.mock_cache_crud,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )

        # Mock the tweet data with a photo
        tweet_data = {
            "extended_entities": {
                "media": [
                    {
                        "media_url_https": "https://pbs.twimg.com/media/example.jpg",
                        "type": "photo",
                    },
                ],
            },
        }

        # Test the private method directly for simplicity
        # noinspection PyUnresolvedReferences
        result = fetcher._TwitterStatusFetcher__resolve_photo_contents(tweet_data, "Additional context")

        # Verify the result contains photo information
        self.assertIsNotNone(result)
        self.assertIn("Photo [1]", result)
        self.assertIn("https://pbs.twimg.com/media/example.jpg", result)
        self.assertIn("A beautiful landscape.", result)

        # Verify the analyzer was called with the correct parameters
        mock_analyzer.assert_called_once()
        call_args = mock_analyzer.call_args
        self.assertEqual(call_args[1]["job_id"], "tweet-123456789")
        self.assertEqual(call_args[1]["image_url"], "https://pbs.twimg.com/media/example.jpg")
        self.assertIsInstance(call_args[1]["open_ai_api_key"], SecretStr)

    @patch("features.web_browsing.twitter_status_fetcher.AuthorizationService")
    @patch("features.web_browsing.twitter_status_fetcher.AccessTokenResolver")
    def test_format_tweet_content_handles_missing_data(self, mock_token_resolver, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user
        mock_token_resolver.return_value.require_access_token_for_tool.return_value = SecretStr("test_token")

        fetcher = TwitterStatusFetcher(
            "123456789",
            self.mock_user,
            self.mock_cache_crud,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )

        # Mock response with missing fields
        response = {
            "data": {
                "data": {
                    "tweetResult": {
                        "result": {
                            "core": {
                                "user_results": {
                                    "result": {
                                        "legacy": {
                                            # Missing name
                                            "screen_name": "testuser",
                                            # Missing description
                                        },
                                    },
                                },
                            },
                            "legacy": {
                                # Missing full_text
                                "lang": "en",
                            },
                        },
                    },
                },
            },
        }

        # noinspection PyUnresolvedReferences
        result = fetcher._TwitterStatusFetcher__resolve_content(response)
        self.assertIn("@testuser · <Anonymous>", result)
        self.assertIn("Bio: \"<No bio>\"", result)
        self.assertIn("<This tweet has no text>", result)


if __name__ == "__main__":
    unittest.main()
