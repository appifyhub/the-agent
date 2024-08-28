import json
from datetime import datetime, timedelta
from typing import Dict, Any

import requests
from tenacity import sleep

from db.crud.tools_cache import ToolsCacheCRUD
from db.schema.tools_cache import ToolsCacheSave, ToolsCache
from features.currencies.supported_currencies import SUPPORTED_FIAT, SUPPORTED_CRYPTO
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

DEFAULT_FIAT = "USD"
COIN_API_URL = "https://rest.coinapi.io"
CURRENCY_API_HOST = "currency-converter5.p.rapidapi.com"
CURRENCY_API_URL = f"https://{CURRENCY_API_HOST}/currency/convert"
CACHE_PREFIX = "exchange-rate-fetcher"
CACHE_TTL = timedelta(minutes = 5)
RATE_LIMIT_DELAY_S = 1.5


class ExchangeRateFetcher(SafePrinterMixin):
    __coin_api_token: str
    __rapid_api_token: str
    __cache_dao: ToolsCacheCRUD

    def __init__(self, coin_api_token: str, rapid_api_token: str, cache_dao: ToolsCacheCRUD):
        super().__init__(config.verbose)
        self.__coin_api_token = coin_api_token
        self.__rapid_api_token = rapid_api_token
        self.__cache_dao = cache_dao

    def execute(
        self,
        base_currency_code: str,
        desired_currency_code: str,
        amount: float = 1.0,
    ) -> Dict[str, float]:
        def as_result(rate: float) -> dict[str, Any]:
            return {
                "from": base_currency_code,
                "to": desired_currency_code,
                "rate": rate,
                "amount": amount,
                "value": rate * amount,
            }

        self.sprint(f"Calculating conversion rate {base_currency_code}/{desired_currency_code} for {amount}")
        if base_currency_code == desired_currency_code:
            self.sprint("Returning the identity conversion rate")
            return as_result(1.0)

        is_base_fiat = base_currency_code in SUPPORTED_FIAT
        is_base_crypto = base_currency_code in SUPPORTED_CRYPTO and base_currency_code != DEFAULT_FIAT
        is_desired_fiat = desired_currency_code in SUPPORTED_FIAT
        is_desired_crypto = desired_currency_code in SUPPORTED_CRYPTO and desired_currency_code != DEFAULT_FIAT
        self.sprint(f"{base_currency_code} is {"F" if is_base_fiat else "C" if is_base_crypto else "??"}")
        self.sprint(f"{desired_currency_code} is {"F" if is_desired_fiat else "C" if is_desired_crypto else "??"}")

        rate_of_one: float
        final_rate: float
        if is_base_fiat and is_desired_fiat:
            self.sprint("Fetching fiat to fiat conversion rate")
            rate_of_one = self.get_fiat_conversion_rate(base_currency_code, desired_currency_code)
            return as_result(rate_of_one)
        elif is_base_crypto and is_desired_crypto:
            self.sprint("Fetching crypto to crypto conversion rate")
            rate_of_one = self.get_crypto_conversion_rate(base_currency_code, desired_currency_code)
            return as_result(rate_of_one)
        elif is_base_fiat and is_desired_crypto:
            # we traverse the exchange rate through the default fiat to get the final rate
            self.sprint("Fetching fiat to crypto conversion rate")
            base_fiat_rate_against_default_fiat = self.get_fiat_conversion_rate(base_currency_code, DEFAULT_FIAT)
            default_fiat_rate_against_crypto = self.get_crypto_conversion_rate(DEFAULT_FIAT, desired_currency_code)
            return as_result(base_fiat_rate_against_default_fiat * default_fiat_rate_against_crypto)
        elif is_base_crypto and is_desired_fiat:
            # basically the same as above, just in reverse
            self.sprint("Fetching crypto to fiat conversion rate")
            base_crypto_rate_against_default_fiat = self.get_crypto_conversion_rate(base_currency_code, DEFAULT_FIAT)
            default_fiat_rate_against_fiat = self.get_fiat_conversion_rate(DEFAULT_FIAT, desired_currency_code)
            return as_result(base_crypto_rate_against_default_fiat * default_fiat_rate_against_fiat)
        else:
            message = f"Unsupported currency conversion: {base_currency_code}/{desired_currency_code}"
            self.sprint(message)
            raise ValueError(message)

    def __cache_key_of(self, a: str, b: str) -> str:
        return self.__cache_dao.create_key(CACHE_PREFIX, f"{a}-{b}")

    def __get_cached_rate_of_one(self, base_currency_code: str, desired_currency_code: str) -> float | None:
        self.sprint(f"Fetching cached rate for {base_currency_code}/{desired_currency_code}")
        # when converting exchange rates, the inverse rule applies:  A / B = 1 / (B / A)
        # let's check the direct requested conversion rate first
        cache_key = self.__cache_key_of(base_currency_code, desired_currency_code)
        cache_entry_db = self.__cache_dao.get(cache_key)
        if cache_entry_db:
            cache_entry = ToolsCache.model_validate(cache_entry_db)
            if not cache_entry.is_expired():
                self.sprint(f"Cache hit for direct conversion and key '{cache_key}'")
                return float(cache_entry.value)
            self.sprint(f"Cache expired for direct conversion and key '{cache_key}'")
        self.sprint(f"Cache miss for direct conversion and key '{cache_key}'")

        # now let's check for the inverse conversion rate
        cache_key = self.__cache_key_of(desired_currency_code, base_currency_code)
        cache_entry_db = self.__cache_dao.get(cache_key)
        if cache_entry_db:
            cache_entry = ToolsCache.model_validate(cache_entry_db)
            if not cache_entry.is_expired():
                self.sprint(f"Cache hit for inverse conversion and key '{cache_key}'")
                return 1.0 / float(cache_entry.value)
            self.sprint(f"Cache expired for inverse conversion and key '{cache_key}'")
        self.sprint(f"Cache miss for inverse conversion and key '{cache_key}'")
        return None

    def __save_rate_to_cache(self, a: str, b: str, rate: float) -> None:
        key = self.__cache_key_of(a, b)
        self.__cache_dao.save(ToolsCacheSave(key = key, value = str(rate), expires_at = datetime.now() + CACHE_TTL))
        self.sprint(f"Cache updated for {a}/{b} and key '{key}'")

    def get_crypto_conversion_rate(self, base_currency_code: str, desired_currency_code: str) -> float:
        self.sprint(f"Fetching crypto conversion rate {base_currency_code}/{desired_currency_code}")
        if base_currency_code not in SUPPORTED_CRYPTO and base_currency_code != DEFAULT_FIAT:
            raise ValueError(f"Unsupported currency: {base_currency_code}")
        if desired_currency_code not in SUPPORTED_CRYPTO and desired_currency_code != DEFAULT_FIAT:
            raise ValueError(f"Unsupported currency: {desired_currency_code}")

        if base_currency_code == desired_currency_code: return 1.0
        cached_rate = self.__get_cached_rate_of_one(base_currency_code, desired_currency_code)
        if cached_rate: return cached_rate

        sleep(RATE_LIMIT_DELAY_S)
        url = f"{COIN_API_URL}/v1/exchangerate/{base_currency_code}/{desired_currency_code}"
        headers = {"X-CoinAPI-Key": self.__coin_api_token}
        response = requests.get(url, headers = headers, timeout = config.web_timeout_s)
        response.raise_for_status()
        data = response.json()

        rate = float(data["rate"])
        if rate:
            self.__save_rate_to_cache(base_currency_code, desired_currency_code, rate)
            return rate
        raise ValueError(f"Invalid rate: {rate}; response data: {json.dumps(json)}")

    def get_fiat_conversion_rate(self, base_currency_code: str, desired_currency_code: str) -> float:
        self.sprint(f"Fetching fiat conversion rate {base_currency_code}/{desired_currency_code}")
        if base_currency_code not in SUPPORTED_FIAT:
            raise ValueError(f"Unsupported currency: {base_currency_code}")
        if desired_currency_code not in SUPPORTED_FIAT:
            raise ValueError(f"Unsupported currency: {desired_currency_code}")

        if base_currency_code == desired_currency_code: return 1.0
        cached_rate = self.__get_cached_rate_of_one(base_currency_code, desired_currency_code)
        if cached_rate: return cached_rate

        sleep(RATE_LIMIT_DELAY_S)
        params = {"format": "json", "from": base_currency_code, "to": desired_currency_code, "amount": "1.0"}
        headers = {"X-RapidAPI-Key": self.__rapid_api_token, "X-RapidAPI-Host": CURRENCY_API_HOST}
        response = requests.get(CURRENCY_API_URL, params = params, headers = headers, timeout = config.web_timeout_s)
        response.raise_for_status()

        rate = float(response.json()["rates"][desired_currency_code]["rate_for_amount"])
        if rate:
            self.__save_rate_to_cache(base_currency_code, desired_currency_code, rate)
            return rate
        raise ValueError(f"Invalid rate: {rate}; response data: {json.dumps(json)}")
