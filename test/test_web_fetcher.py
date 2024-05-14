import unittest

import requests_mock
from requests_mock.mocker import Mocker

from config import Config
from web_fetcher import WebFetcher


DEFAULT_URL = "https://httpbin.org/get"

class WebFetcherTest(unittest.TestCase):
    __config = Config(
        def_verbose = True,
        def_web_retries = 1,
        def_web_retry_delay_s = 0,
        def_web_timeout_s = 1,
    )

    @requests_mock.Mocker()
    def test_auto_fetch_disabled(self, m: Mocker):
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        fetcher = WebFetcher(DEFAULT_URL, self.__config)
        self.assertEqual(fetcher.html, None)

    @requests_mock.Mocker()
    def test_auto_fetch_enabled(self, m: Mocker):
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        fetcher = WebFetcher(DEFAULT_URL, self.__config, auto_fetch = True)
        self.assertEqual(fetcher.html, "data")

    @requests_mock.Mocker()
    def test_fetch_html_ok(self, m: Mocker):
        m.get(DEFAULT_URL, text = "data", status_code = 200)
        fetcher = WebFetcher(DEFAULT_URL, self.__config)
        self.assertEqual(fetcher.fetch_html(), "data")
        self.assertEqual(fetcher.html, "data")

    @requests_mock.Mocker()
    def test_fetch_html_error(self, m: Mocker):
        m.get(DEFAULT_URL, status_code = 404)
        fetcher = WebFetcher(DEFAULT_URL, self.__config, auto_fetch = True)
        self.assertEqual(fetcher.html, None)
