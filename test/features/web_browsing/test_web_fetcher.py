import json
import unittest
from datetime import datetime
from unittest.mock import MagicMock

import requests_mock
from requests_mock.mocker import Mocker

from db.crud.tools_cache import ToolsCacheCRUD
from db.schema.tools_cache import ToolsCache
from features.web_browsing.web_fetcher import WebFetcher, CACHE_TTL_HTML, CACHE_TTL_JSON, DEFAULT_HEADERS
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
            expires_at = datetime.now() + CACHE_TTL_HTML,
        )
        self.cache_entry_json = ToolsCache(
            key = "test_cache_key",
            value = self.cached_json,
            expires_at = datetime.now() + CACHE_TTL_JSON,
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
