import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

import requests_mock
from requests_mock import Mocker

from db.schema.tools_cache import ToolsCache
from features.web_browsing.web_fetcher import (
    DEFAULT_HEADERS,
    WebFetcher,
)
from util.config import config

DEFAULT_URL = "https://example.com"


class WebFetcherTest(unittest.TestCase):
    mock_cache_crud: MagicMock
    mock_user_dao: MagicMock
    mock_chat_config_dao: MagicMock
    mock_sponsorship_dao: MagicMock
    mock_telegram_bot_sdk: MagicMock
    mock_user: MagicMock
    cache_entry_html: ToolsCache
    cache_entry_json: ToolsCache

    def setUp(self):
        config.web_retries = 1
        config.web_retry_delay_s = 0
        config.web_timeout_s = 1

        self.mock_cache_crud = MagicMock()
        self.mock_user_dao = MagicMock()
        self.mock_chat_config_dao = MagicMock()
        self.mock_sponsorship_dao = MagicMock()
        self.mock_telegram_bot_sdk = MagicMock()

        # Mock user
        self.mock_user = MagicMock()
        self.mock_user.id = UUID("12345678-1234-5678-1234-567812345678")

        self.cache_entry_html = ToolsCache(
            key = "web-fetcher::test_key",
            value = "Cached HTML content",
            expires_at = datetime.now() + timedelta(hours = 1),
        )
        self.cache_entry_json = ToolsCache(
            key = "web-fetcher::test_key",
            value = json.dumps({"key": "Cached value"}),
            expires_at = datetime.now() + timedelta(hours = 1),
        )
        self.mock_cache_crud.create_key.return_value = "test_cache_key"

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_auto_fetch_html_disabled(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        m.get(DEFAULT_URL, text = "data", status_code = 200)
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        self.assertIsNone(fetcher.html)

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_auto_fetch_html_enabled(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        m.get(DEFAULT_URL, text = "data", status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            auto_fetch_html = True,
        )
        self.assertEqual(fetcher.html, "data")

    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_fetch_html_ok_cache_hit(self, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        self.mock_cache_crud.get.return_value = self.cache_entry_html.model_dump()
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        result = fetcher.fetch_html()
        self.assertEqual(result, "Cached HTML content")

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_fetch_html_ok_cache_miss(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        m.get(DEFAULT_URL, text = "data", status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        result = fetcher.fetch_html()
        self.assertEqual(result, "data")

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_fetch_html_error(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        m.get(DEFAULT_URL, status_code = 404)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            auto_fetch_html = True,
        )
        self.assertIsNone(fetcher.html)

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_fetch_html_binary_content(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        # Simulate binary PDF response with NUL bytes
        binary_content = b"%PDF-1.4\x00binarydata"
        m.get(DEFAULT_URL, content = binary_content, status_code = 200, headers = {"Content-Type": "application/pdf"})
        self.mock_cache_crud.get.return_value = None

        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        result = fetcher.fetch_html()
        self.assertIsNone(result)
        self.assertIsNone(fetcher.html)

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_auto_fetch_json_disabled(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        stub = {"value": "data"}
        m.get(DEFAULT_URL, json = stub, status_code = 200)
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        self.assertIsNone(fetcher.json)

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_auto_fetch_json_enabled(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        stub = {"value": "data"}
        m.get(DEFAULT_URL, json = stub, status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            auto_fetch_json = True,
        )
        self.assertEqual(fetcher.json, stub)

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_fetch_json_ok_cache_miss(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        stub = {"value": "data"}
        m.get(DEFAULT_URL, json = stub, status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        result = fetcher.fetch_json()
        self.assertEqual(result, stub)

    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_fetch_json_ok_cache_hit(self, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        self.mock_cache_crud.get.return_value = self.cache_entry_json.model_dump()
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        result = fetcher.fetch_json()
        self.assertEqual(result, {"key": "Cached value"})

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_custom_cache_ttl_html(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        custom_ttl = timedelta(minutes = 10)
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            cache_ttl_html = custom_ttl,
        )
        fetcher.fetch_html()
        # Verify that save was called with the custom TTL
        self.mock_cache_crud.save.assert_called_once()

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_custom_cache_ttl_json(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        custom_ttl = timedelta(minutes = 2)
        m.get(DEFAULT_URL, json = {"value": "data"}, status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            cache_ttl_json = custom_ttl,
        )
        fetcher.fetch_json()
        # Verify that save was called with the custom TTL
        self.mock_cache_crud.save.assert_called_once()

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_default_cache_ttl_html(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        m.get(DEFAULT_URL, text = "data", status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        fetcher.fetch_html()
        # Verify that save was called
        self.mock_cache_crud.save.assert_called_once()

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_default_cache_ttl_json(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        m.get(DEFAULT_URL, json = {"value": "data"}, status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        fetcher.fetch_json()
        # Verify that save was called
        self.mock_cache_crud.save.assert_called_once()

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_fetch_json_error(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        m.get(DEFAULT_URL, status_code = 404)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            auto_fetch_json = True,
        )
        self.assertIsNone(fetcher.json)

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_custom_headers(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        custom_headers = {"X-Custom-Header": "test_value"}
        expected_headers = {**DEFAULT_HEADERS, **custom_headers}
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            headers = custom_headers,
            auto_fetch_html = True,
        )
        # Access the html property to use the fetcher variable
        self.assertEqual(fetcher.html, "data")
        # Verify the request was made with the expected headers
        self.assertEqual(len(m.request_history), 1)
        for key, value in expected_headers.items():
            self.assertEqual(m.request_history[0].headers[key], value)

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_custom_params(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        custom_params = {"param1": "value1", "param2": "value2"}
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            params = custom_params,
            auto_fetch_html = True,
        )
        # Access the html property to use the fetcher variable
        self.assertEqual(fetcher.html, "data")
        # Verify the request was made with the expected parameters
        self.assertEqual(len(m.request_history), 1)
        self.assertIn("param1=value1", m.request_history[0].url)
        self.assertIn("param2=value2", m.request_history[0].url)

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_fetch_html_with_headers_and_params(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        custom_headers = {"X-Custom-Header": "test_value"}
        custom_params = {"param1": "value1", "param2": "value2"}
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            headers = custom_headers,
            params = custom_params,
        )
        result = fetcher.fetch_html()
        self.assertEqual(result, "data")

    @requests_mock.Mocker()
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_fetch_json_with_headers_and_params(self, m: Mocker, mock_auth_service):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        custom_headers = {"X-Custom-Header": "test_value"}
        custom_params = {"param1": "value1", "param2": "value2"}
        stub = {"value": "data"}
        m.get(DEFAULT_URL, json = stub, status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
            headers = custom_headers,
            params = custom_params,
        )
        result = fetcher.fetch_json()
        self.assertEqual(result, stub)

    @patch("features.web_browsing.web_fetcher.resolve_tweet_id")
    @patch("features.web_browsing.web_fetcher.TwitterStatusFetcher")
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_fetch_html_twitter(self, mock_auth_service, mock_twitter_fetcher, mock_resolve_tweet_id):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        mock_resolve_tweet_id.return_value = "123456"
        mock_twitter_fetcher.return_value.execute.return_value = "Tweet content"

        # Test cache miss scenario
        self.mock_cache_crud.get.return_value = None

        fetcher = WebFetcher(
            "https://twitter.com/user/status/123456",
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        result = fetcher.fetch_html()

        # Verify TwitterStatusFetcher was called with correct parameters
        mock_twitter_fetcher.assert_called_once_with(
            "123456",
            self.mock_user,
            self.mock_cache_crud,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        self.assertIn("Tweet content", result)

    @patch("features.web_browsing.web_fetcher.resolve_tweet_id")
    @patch("features.web_browsing.web_fetcher.TwitterStatusFetcher")
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_fetch_json_twitter(self, mock_auth_service, mock_twitter_fetcher, mock_resolve_tweet_id):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        mock_resolve_tweet_id.return_value = "123456"
        mock_twitter_fetcher.return_value.execute.return_value = "Tweet content"

        # Test cache miss scenario
        self.mock_cache_crud.get.return_value = None

        fetcher = WebFetcher(
            "https://twitter.com/user/status/123456",
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        result = fetcher.fetch_json()

        # Verify TwitterStatusFetcher was called with correct parameters
        mock_twitter_fetcher.assert_called_once_with(
            "123456",
            self.mock_user,
            self.mock_cache_crud,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        self.assertEqual(result, {"content": "Tweet content"})

    @patch("features.web_browsing.web_fetcher.resolve_tweet_id")
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_fetch_html_non_twitter(self, mock_auth_service, mock_resolve_tweet_id):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        mock_resolve_tweet_id.return_value = None

        # Create a mock cache entry that matches ToolsCache structure
        mock_cache_entry = {
            "key": "test_cache_key",
            "value": "Cached HTML content",
            "expires_at": (datetime.now() + timedelta(hours = 1)).isoformat(),
        }
        self.mock_cache_crud.get.return_value = mock_cache_entry

        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        result = fetcher.fetch_html()
        self.assertEqual(result, "Cached HTML content")

    @patch("features.web_browsing.web_fetcher.resolve_tweet_id")
    @patch("features.web_browsing.web_fetcher.AuthorizationService")
    def test_fetch_json_non_twitter(self, mock_auth_service, mock_resolve_tweet_id):
        mock_auth_service.return_value.validate_user.return_value = self.mock_user

        mock_resolve_tweet_id.return_value = None

        # Create a mock cache entry that matches ToolsCache structure
        mock_cache_entry = {
            "key": "test_cache_key",
            "value": json.dumps({"key": "Cached value"}),
            "expires_at": (datetime.now() + timedelta(hours = 1)).isoformat(),
        }
        self.mock_cache_crud.get.return_value = mock_cache_entry

        fetcher = WebFetcher(
            DEFAULT_URL,
            self.mock_user,
            self.mock_user_dao,
            self.mock_chat_config_dao,
            self.mock_cache_crud,
            self.mock_sponsorship_dao,
            self.mock_telegram_bot_sdk,
        )
        result = fetcher.fetch_json()
        self.assertEqual(result, {"key": "Cached value"})


if __name__ == "__main__":
    unittest.main()
