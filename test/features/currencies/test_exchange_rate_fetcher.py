import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import requests_mock
from requests_mock.mocker import Mocker

from db.crud.tools_cache import ToolsCacheCRUD
from db.schema.tools_cache import ToolsCache
from features.currencies.exchange_rate_fetcher import ExchangeRateFetcher, CACHE_TTL
from util.config import config


class ExchangeRateFetcherTest(unittest.TestCase):
    cached_rate: str
    cache_entry: ToolsCache
    mock_cache_crud: ToolsCacheCRUD

    def setUp(self):
        config.web_timeout_s = 1
        self.cached_rate = "1.5"
        self.cache_entry = ToolsCache(
            key = "test_cache_key",
            value = self.cached_rate,
            expires_at = datetime.now() + CACHE_TTL,
        )
        self.mock_cache_crud = MagicMock()
        self.mock_cache_crud.create_key.return_value = "test_cache_key"

    @patch("features.currencies.exchange_rate_fetcher.sleep", return_value = None)
    @requests_mock.Mocker()
    def test_execute_same_currency(self, m: Mocker, mock_sleep):
        fetcher = ExchangeRateFetcher("coin_api_token", "rapid_api_token", self.mock_cache_crud)
        result = fetcher.execute("USD", "USD", 100)
        self.assertEqual(result, {"from": "USD", "to": "USD", "rate": 1.0, "amount": 100, "value": 100})

    @patch("features.currencies.exchange_rate_fetcher.sleep", return_value = None)
    @patch("features.currencies.exchange_rate_fetcher.ExchangeRateFetcher.get_fiat_conversion_rate")
    def test_execute_fiat_to_fiat(self, mock_get_fiat, mock_sleep):
        mock_get_fiat.return_value = 0.85
        fetcher = ExchangeRateFetcher("coin_api_token", "rapid_api_token", self.mock_cache_crud)
        result = fetcher.execute("USD", "EUR", 100)
        self.assertEqual(result, {"from": "USD", "to": "EUR", "rate": 0.85, "amount": 100, "value": 85})

    @patch("features.currencies.exchange_rate_fetcher.sleep", return_value = None)
    @patch("features.currencies.exchange_rate_fetcher.ExchangeRateFetcher.get_crypto_conversion_rate")
    def test_execute_crypto_to_crypto(self, mock_get_crypto, mock_sleep):
        mock_get_crypto.return_value = 15.5
        fetcher = ExchangeRateFetcher("coin_api_token", "rapid_api_token", self.mock_cache_crud)
        result = fetcher.execute("BTC", "ETH", 1)
        self.assertEqual(result, {"from": "BTC", "to": "ETH", "rate": 15.5, "amount": 1, "value": 15.5})

    @patch("features.currencies.exchange_rate_fetcher.sleep", return_value = None)
    @patch("features.currencies.exchange_rate_fetcher.ExchangeRateFetcher.get_fiat_conversion_rate")
    @patch("features.currencies.exchange_rate_fetcher.ExchangeRateFetcher.get_crypto_conversion_rate")
    def test_execute_fiat_to_crypto(self, mock_get_crypto, mock_get_fiat, mock_sleep):
        mock_get_fiat.return_value = 1.2  # EUR to USD
        mock_get_crypto.return_value = 0.000025  # USD to BTC (1 BTC = 40,000 USD)
        fetcher = ExchangeRateFetcher("coin_api_token", "rapid_api_token", self.mock_cache_crud)
        result = fetcher.execute("EUR", "BTC", 1000000)  # 1 million EUR
        expected_rate = 1.2 * 0.000025
        expected_result = {"from": "EUR", "to": "BTC", "rate": expected_rate, "amount": 1000000, "value": 30}
        self.assertEqual(result, expected_result)

    @patch("features.currencies.exchange_rate_fetcher.sleep", return_value = None)
    def test_execute_unsupported_currency(self, mock_sleep):
        fetcher = ExchangeRateFetcher("coin_api_token", "rapid_api_token", self.mock_cache_crud)
        with self.assertRaises(ValueError):
            fetcher.execute("USD", "XYZ", 100)

    @patch("features.currencies.exchange_rate_fetcher.sleep", return_value = None)
    @requests_mock.Mocker()
    def test_get_crypto_conversion_rate_cache_hit(self, m: Mocker, mock_sleep):
        self.mock_cache_crud.get.return_value = self.cache_entry.model_dump()
        fetcher = ExchangeRateFetcher("coin_api_token", "rapid_api_token", self.mock_cache_crud)
        rate = fetcher.get_crypto_conversion_rate("BTC", "ETH")
        self.assertEqual(rate, 1.5)
        # noinspection PyUnresolvedReferences
        m.assert_not_called()

    @patch("features.currencies.exchange_rate_fetcher.sleep", return_value = None)
    @patch("features.currencies.exchange_rate_fetcher.requests.get")
    def test_get_crypto_conversion_rate_cache_miss(self, mock_get, mock_sleep):
        self.mock_cache_crud.get.return_value = None
        mock_response = MagicMock()
        mock_response.json.return_value = {"rate": 15.5}
        mock_get.return_value = mock_response
        fetcher = ExchangeRateFetcher("coin_api_token", "rapid_api_token", self.mock_cache_crud)
        rate = fetcher.get_crypto_conversion_rate("BTC", "ETH")
        self.assertEqual(rate, 15.5)
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_called_once()

    @patch("features.currencies.exchange_rate_fetcher.sleep", return_value = None)
    @requests_mock.Mocker()
    def test_get_fiat_conversion_rate_cache_hit(self, m: Mocker, mock_sleep):
        self.mock_cache_crud.get.return_value = self.cache_entry.model_dump()
        fetcher = ExchangeRateFetcher("coin_api_token", "rapid_api_token", self.mock_cache_crud)
        rate = fetcher.get_fiat_conversion_rate("USD", "EUR")
        self.assertEqual(rate, 1.5)
        # noinspection PyUnresolvedReferences
        m.assert_not_called()

    @patch("features.currencies.exchange_rate_fetcher.sleep", return_value = None)
    @patch("features.currencies.exchange_rate_fetcher.requests.get")
    def test_get_fiat_conversion_rate_cache_miss(self, mock_get, mock_sleep):
        self.mock_cache_crud.get.return_value = None
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"EUR": {"rate_for_amount": "0.85"}}}
        mock_get.return_value = mock_response
        fetcher = ExchangeRateFetcher("coin_api_token", "rapid_api_token", self.mock_cache_crud)
        rate = fetcher.get_fiat_conversion_rate("USD", "EUR")
        self.assertEqual(rate, 0.85)
        # noinspection PyUnresolvedReferences
        self.mock_cache_crud.save.assert_called_once()
