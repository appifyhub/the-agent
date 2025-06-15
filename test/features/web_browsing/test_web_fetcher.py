import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import requests_mock
from requests_mock.mocker import Mocker

from db.crud.tools_cache import ToolsCacheCRUD
from db.schema.tools_cache import ToolsCache
from features.web_browsing.web_fetcher import (
    DEFAULT_CACHE_TTL_HTML,
    DEFAULT_CACHE_TTL_JSON,
    DEFAULT_HEADERS,
    WebFetcher,
)
from util.config import config

DEFAULT_URL = "https://example.org"


class WebFetcherTest(unittest.TestCase):
    cached_html: str
    cache_entry_html: ToolsCache
    cached_json: str
    cache_entry_json: ToolsCache
    mock_cache_crud: ToolsCacheCRUD

    def setUp(self):
        config.web_retries = 1
        config.web_retry_delay_s = 0
        config.web_timeout_s = 1

        self.mock_cache_crud = MagicMock()
        self.cached_html = "data"
        self.cached_json = json.dumps({"value": "data"})
        self.cache_entry_html = ToolsCache(
            key = "test_cache_key",
            value = self.cached_html,
            expires_at = datetime.now() + DEFAULT_CACHE_TTL_HTML,
        )
        self.cache_entry_json = ToolsCache(
            key = "test_cache_key",
            value = self.cached_json,
            expires_at = datetime.now() + DEFAULT_CACHE_TTL_JSON,
        )
        self.mock_cache_crud.create_key.return_value = "test_cache_key"

    @requests_mock.Mocker()
    def test_auto_fetch_html_disabled(self, m: Mocker):
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud)
        self.assertIsNone(fetcher.html)

    @requests_mock.Mocker()
    def test_auto_fetch_html_enabled(self, m: Mocker):
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud, auto_fetch_html = True)
        self.assertEqual(fetcher.html, "data")

    @requests_mock.Mocker()
    def test_fetch_html_ok_cache_miss(self, m: Mocker):
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud)
        self.assertEqual(fetcher.fetch_html(), "data")
        self.assertEqual(fetcher.html, "data")
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_called_once()

    def test_fetch_html_ok_cache_hit(self):
        self.mock_cache_crud.get.return_value = self.cache_entry_html.model_dump()
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud)
        self.assertEqual(fetcher.fetch_html(), "data")
        self.assertEqual(fetcher.html, "data")
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_not_called()

    @requests_mock.Mocker()
    def test_fetch_html_error(self, m: Mocker):
        m.get(DEFAULT_URL, status_code = 404)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud, auto_fetch_html = True)
        self.assertIsNone(fetcher.html)

    @requests_mock.Mocker()
    def test_fetch_html_binary_content(self, m: Mocker):
        # Simulate binary PDF response with NUL bytes
        binary_content = b"%PDF-1.4\x00binarydata"
        m.get(DEFAULT_URL, content=binary_content, status_code=200, headers={"Content-Type": "application/pdf"})
        self.mock_cache_crud.get.return_value = None

        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud)
        result = fetcher.fetch_html()

        self.assertIsNone(result)
        self.assertIsNone(fetcher.html)
        # Ensure nothing was cached
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_not_called()

    @requests_mock.Mocker()
    def test_auto_fetch_json_disabled(self, m: Mocker):
        stub = {"value": "data"}
        m.get(DEFAULT_URL, json = stub, status_code = 200)
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud)
        self.assertIsNone(fetcher.json)

    @requests_mock.Mocker()
    def test_auto_fetch_json_enabled(self, m: Mocker):
        stub = {"value": "data"}
        m.get(DEFAULT_URL, json = stub, status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud, auto_fetch_json = True)
        self.assertEqual(fetcher.json, stub)

    @requests_mock.Mocker()
    def test_fetch_json_ok_cache_miss(self, m: Mocker):
        stub = {"value": "data"}
        m.get(DEFAULT_URL, json = stub, status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud)
        self.assertEqual(fetcher.fetch_json(), stub)
        self.assertEqual(fetcher.json, stub)
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_called_once()

    def test_fetch_json_ok_cache_hit(self):
        self.mock_cache_crud.get.return_value = self.cache_entry_json.model_dump()
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud)
        self.assertEqual(fetcher.fetch_json(), {"value": "data"})
        self.assertEqual(fetcher.json, {"value": "data"})
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_not_called()

    @requests_mock.Mocker()
    def test_custom_cache_ttl_html(self, m: Mocker):
        custom_ttl = timedelta(minutes = 10)
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud, cache_ttl_html = custom_ttl)
        fetcher.fetch_html()
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_called_once()
        # noinspection PyUnresolvedReferences
        saved_cache = self.mock_cache_crud.save.call_args[0][0]
        self.assertAlmostEqual(saved_cache.expires_at, datetime.now() + custom_ttl, delta = timedelta(seconds = 1))

    @requests_mock.Mocker()
    def test_custom_cache_ttl_json(self, m: Mocker):
        custom_ttl = timedelta(minutes = 2)
        m.get(DEFAULT_URL, json = {"value": "data"}, status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud, cache_ttl_json = custom_ttl)
        fetcher.fetch_json()
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_called_once()
        # noinspection PyUnresolvedReferences
        saved_cache = self.mock_cache_crud.save.call_args[0][0]
        self.assertAlmostEqual(saved_cache.expires_at, datetime.now() + custom_ttl, delta = timedelta(seconds = 1))

    @requests_mock.Mocker()
    def test_default_cache_ttl_html(self, m: Mocker):
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud)
        fetcher.fetch_html()
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_called_once()
        # noinspection PyUnresolvedReferences
        saved_cache = self.mock_cache_crud.save.call_args[0][0]
        self.assertAlmostEqual(
            saved_cache.expires_at,
            datetime.now() + DEFAULT_CACHE_TTL_HTML,
            delta = timedelta(seconds = 1),
        )

    @requests_mock.Mocker()
    def test_default_cache_ttl_json(self, m: Mocker):
        m.get(DEFAULT_URL, json = {"value": "data"}, status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud)
        fetcher.fetch_json()
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_called_once()
        # noinspection PyUnresolvedReferences
        saved_cache = self.mock_cache_crud.save.call_args[0][0]
        self.assertAlmostEqual(
            saved_cache.expires_at,
            datetime.now() + DEFAULT_CACHE_TTL_JSON,
            delta = timedelta(seconds = 1),
        )

    @requests_mock.Mocker()
    def test_fetch_json_error(self, m: Mocker):
        m.get(DEFAULT_URL, status_code = 404)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud, auto_fetch_json = True)
        self.assertIsNone(fetcher.json)

    @requests_mock.Mocker()
    def test_custom_headers(self, m: Mocker):
        custom_headers = {"X-Custom-Header": "test_value"}
        expected_headers = {**DEFAULT_HEADERS, **custom_headers}
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud, headers = custom_headers, auto_fetch_html = True)
        self.assertEqual(fetcher.html, "data")
        self.assertEqual(m.last_request.headers.get("X-Custom-Header"), "test_value")
        for key, value in expected_headers.items():
            self.assertEqual(m.last_request.headers.get(key), value)

    @requests_mock.Mocker()
    def test_custom_params(self, m: Mocker):
        custom_params = {"param1": "value1", "param2": "value2"}
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud, params = custom_params, auto_fetch_html = True)
        self.assertEqual(fetcher.html, "data")
        expected_qs = {k: [v] for k, v in custom_params.items()}
        self.assertEqual(m.last_request.qs, expected_qs)

    @requests_mock.Mocker()
    def test_fetch_html_with_headers_and_params(self, m: Mocker):
        custom_headers = {"X-Custom-Header": "test_value"}
        custom_params = {"param1": "value1", "param2": "value2"}
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud, headers = custom_headers, params = custom_params)
        self.assertEqual(fetcher.fetch_html(), "data")
        self.assertEqual(m.last_request.headers.get("X-Custom-Header"), "test_value")
        expected_qs = {k: [v] for k, v in custom_params.items()}
        self.assertEqual(m.last_request.qs, expected_qs)

    @requests_mock.Mocker()
    def test_fetch_json_with_headers_and_params(self, m: Mocker):
        custom_headers = {"X-Custom-Header": "test_value"}
        custom_params = {"param1": "value1", "param2": "value2"}
        stub = {"value": "data"}
        m.get(DEFAULT_URL, json = stub, status_code = 200)
        self.mock_cache_crud.get.return_value = None
        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud, headers = custom_headers, params = custom_params)
        self.assertEqual(fetcher.fetch_json(), stub)
        self.assertEqual(m.last_request.headers.get("X-Custom-Header"), "test_value")
        expected_qs = {k: [v] for k, v in custom_params.items()}
        self.assertEqual(m.last_request.qs, expected_qs)

    @patch("features.web_browsing.web_fetcher.resolve_tweet_id")
    @patch("features.web_browsing.web_fetcher.TwitterStatusFetcher")
    def test_fetch_html_twitter(self, mock_twitter_fetcher, mock_resolve_tweet_id):
        mock_resolve_tweet_id.return_value = "123456"
        mock_twitter_fetcher.return_value.execute.return_value = "Tweet content"

        # Test cache miss scenario
        self.mock_cache_crud.get.return_value = None

        fetcher = WebFetcher("https://twitter.com/user/status/123456", self.mock_cache_crud)
        result = fetcher.fetch_html()

        expected_html = "<html><body>\n<p>\nTweet content\n</p>\n</body></html>"
        self.assertEqual(result, expected_html)
        self.assertEqual(fetcher.html, expected_html)
        mock_twitter_fetcher.assert_called_once_with("123456", self.mock_cache_crud)

        # Test cache hit scenario
        mock_cache_entry = {
            "key": "test_cache_key",
            "value": expected_html,
            "expires_at": (datetime.now() + timedelta(hours = 1)).isoformat(),
        }
        self.mock_cache_crud.get.return_value = mock_cache_entry

        result = fetcher.fetch_html()
        self.assertEqual(result, expected_html)
        self.assertEqual(fetcher.html, expected_html)

    @patch("features.web_browsing.web_fetcher.resolve_tweet_id")
    @patch("features.web_browsing.web_fetcher.TwitterStatusFetcher")
    def test_fetch_json_twitter(self, mock_twitter_fetcher, mock_resolve_tweet_id):
        mock_resolve_tweet_id.return_value = "123456"
        mock_twitter_fetcher.return_value.execute.return_value = "Tweet content"

        # Test cache miss scenario
        self.mock_cache_crud.get.return_value = None

        fetcher = WebFetcher("https://twitter.com/user/status/123456", self.mock_cache_crud)
        result = fetcher.fetch_json()

        expected_json = {"content": "Tweet content"}
        self.assertEqual(result, expected_json)
        self.assertEqual(fetcher.json, expected_json)
        mock_twitter_fetcher.assert_called_once_with("123456", self.mock_cache_crud)

        # Test cache hit scenario
        mock_cache_entry = {
            "key": "test_cache_key",
            "value": json.dumps(expected_json),
            "expires_at": (datetime.now() + timedelta(hours = 1)).isoformat(),
        }
        self.mock_cache_crud.get.return_value = mock_cache_entry

        result = fetcher.fetch_json()
        self.assertEqual(result, expected_json)
        self.assertEqual(fetcher.json, expected_json)

    @patch("features.web_browsing.web_fetcher.resolve_tweet_id")
    def test_fetch_html_non_twitter(self, mock_resolve_tweet_id):
        mock_resolve_tweet_id.return_value = None

        # Create a mock cache entry that matches ToolsCache structure
        mock_cache_entry = {
            "key": "test_cache_key",
            "value": "Cached HTML content",
            "expires_at": (datetime.now() + timedelta(hours = 1)).isoformat(),
        }
        self.mock_cache_crud.get.return_value = mock_cache_entry

        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud)
        result = fetcher.fetch_html()

        self.assertEqual(result, "Cached HTML content")
        self.assertEqual(fetcher.html, "Cached HTML content")

        # Test cache miss scenario
        self.mock_cache_crud.get.return_value = None
        with requests_mock.Mocker() as m:
            m.get(DEFAULT_URL, text = "Regular HTML content", status_code = 200)
            result = fetcher.fetch_html()

        self.assertEqual(result, "Regular HTML content")
        self.assertEqual(fetcher.html, "Regular HTML content")

    @patch("features.web_browsing.web_fetcher.resolve_tweet_id")
    def test_fetch_json_non_twitter(self, mock_resolve_tweet_id):
        mock_resolve_tweet_id.return_value = None

        # Create a mock cache entry that matches ToolsCache structure
        mock_cache_entry = {
            "key": "test_cache_key",
            "value": json.dumps({"key": "Cached value"}),
            "expires_at": (datetime.now() + timedelta(hours = 1)).isoformat(),
        }
        self.mock_cache_crud.get.return_value = mock_cache_entry

        fetcher = WebFetcher(DEFAULT_URL, self.mock_cache_crud)
        result = fetcher.fetch_json()

        self.assertEqual(result, {"key": "Cached value"})
        self.assertEqual(fetcher.json, {"key": "Cached value"})

        # Test cache miss scenario
        self.mock_cache_crud.get.return_value = None
        with requests_mock.Mocker() as m:
            m.get(DEFAULT_URL, json = {"key": "Fresh value"}, status_code = 200)
            result = fetcher.fetch_json()

        self.assertEqual(result, {"key": "Fresh value"})
        self.assertEqual(fetcher.json, {"key": "Fresh value"})
