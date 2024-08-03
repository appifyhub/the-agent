import unittest

import requests_mock
from requests_mock.mocker import Mocker

from features.web_fetcher import WebFetcher
from util.config import config

DEFAULT_URL = "https://httpbin.org/get"


class WebFetcherTest(unittest.TestCase):

    def setUp(self):
        config.verbose = True
        config.web_retries = 1
        config.web_retry_delay_s = 0
        config.web_timeout_s = 1

    @requests_mock.Mocker()
    def test_auto_fetch_html_disabled(self, m: Mocker):
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        fetcher = WebFetcher(DEFAULT_URL)
        self.assertIsNone(fetcher.html)

    @requests_mock.Mocker()
    def test_auto_fetch_html_enabled(self, m: Mocker):
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        fetcher = WebFetcher(DEFAULT_URL, auto_fetch_html = True)
        self.assertEqual(fetcher.html, "data")

    @requests_mock.Mocker()
    def test_fetch_html_ok(self, m: Mocker):
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        fetcher = WebFetcher(DEFAULT_URL)
        self.assertEqual(fetcher.fetch_html(), "data")
        self.assertEqual(fetcher.html, "data")

    @requests_mock.Mocker()
    def test_fetch_html_error(self, m: Mocker):
        m.get(DEFAULT_URL, status_code = 404)
        fetcher = WebFetcher(DEFAULT_URL, auto_fetch_html = True)
        self.assertIsNone(fetcher.html)

    @requests_mock.Mocker()
    def test_auto_fetch_json_disabled(self, m: Mocker):
        stub = {"value": "data"}
        m.get(DEFAULT_URL, json = stub, status_code = 200)
        fetcher = WebFetcher(DEFAULT_URL)
        self.assertIsNone(fetcher.json)

    @requests_mock.Mocker()
    def test_auto_fetch_json_enabled(self, m: Mocker):
        stub = {"value": "data"}
        m.get(DEFAULT_URL, json = stub, status_code = 200)
        fetcher = WebFetcher(DEFAULT_URL, auto_fetch_json = True)
        self.assertEqual(fetcher.json, stub)

    @requests_mock.Mocker()
    def test_fetch_json_ok(self, m: Mocker):
        stub = {"value": "data"}
        m.get(DEFAULT_URL, json = stub, status_code = 200)
        fetcher = WebFetcher(DEFAULT_URL)
        self.assertEqual(fetcher.fetch_json(), stub)
        self.assertEqual(fetcher.json, stub)

    @requests_mock.Mocker()
    def test_fetch_json_error(self, m: Mocker):
        m.get(DEFAULT_URL, status_code = 404)
        fetcher = WebFetcher(DEFAULT_URL, auto_fetch_json = True)
        self.assertIsNone(fetcher.json)
