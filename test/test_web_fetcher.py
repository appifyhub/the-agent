import unittest

import requests_mock
from requests_mock.mocker import Mocker

from web_fetcher import WebFetcher


DEFAULT_URL = "https://example.com"

class WebFetcherTest(unittest.TestCase):

    @requests_mock.Mocker()
    def test_auto_fetch_disabled(self, m: Mocker):
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        fetcher = WebFetcher(DEFAULT_URL)
        self.assertEqual(fetcher.html, None)

    @requests_mock.Mocker()
    def test_auto_fetch_enabled(self, m: Mocker):
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        fetcher = WebFetcher(DEFAULT_URL, auto_fetch = True)
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
        fetcher = WebFetcher(DEFAULT_URL, auto_fetch = True)
        self.assertEqual(fetcher.html, None)
