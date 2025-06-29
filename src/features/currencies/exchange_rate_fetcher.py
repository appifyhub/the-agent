import json
from datetime import datetime, timedelta
from time import sleep
from typing import Any, Dict
from uuid import UUID

from api.authorization_service import AuthorizationService
from db.crud.chat_config import ChatConfigCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.tools_cache import ToolsCacheCRUD
from db.crud.user import UserCRUD
from db.schema.tools_cache import ToolsCache, ToolsCacheSave
from db.schema.user import User
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.currencies.supported_currencies import SUPPORTED_CRYPTO, SUPPORTED_FIAT
from features.external_tools.access_token_resolver import AccessTokenResolver
from features.external_tools.external_tool_library import CRYPTO_CURRENCY_EXCHANGE, FIAT_CURRENCY_EXCHANGE
from features.web_browsing.web_fetcher import WebFetcher
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

DEFAULT_FIAT = "USD"
CACHE_PREFIX = "exchange-rate-fetcher"
CACHE_TTL = timedelta(minutes = 5)
RATE_LIMIT_DELAY_S = 1


class ExchangeRateFetcher(SafePrinterMixin):
    __cache_dao: ToolsCacheCRUD
    __token_resolver: AccessTokenResolver

    def __init__(
        self,
        invoker_user: str | UUID | User,
        user_dao: UserCRUD,
        chat_config_dao: ChatConfigCRUD,
        cache_dao: ToolsCacheCRUD,
        sponsorship_dao: SponsorshipCRUD,
        telegram_sdk: TelegramBotSDK,
    ):
        super().__init__(config.verbose)
        self.__cache_dao = cache_dao
        authorization_service = AuthorizationService(telegram_sdk, user_dao, chat_config_dao)
        invoker_user = authorization_service.validate_user(invoker_user)

        self.__token_resolver = AccessTokenResolver(invoker_user, user_dao, sponsorship_dao)
        self.sprint(f"ExchangeRateFetcher initialized with user '{invoker_user.id.hex}'")

    def execute(
        self,
        base_currency_code: str,
        desired_currency_code: str,
        amount: float = 1.0,
    ) -> Dict[str, Any]:
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

    # when converting exchange rates, the inverse rule applies:  A / B = 1 / (B / A)
    def __get_cached_rate_of_one(self, base_currency_code: str, desired_currency_code: str) -> float | None:
        # let's check the direct requested conversion rate first
        self.sprint(f"Fetching cached rate for {base_currency_code}/{desired_currency_code}")
        cache_key = self.__cache_key_of(base_currency_code, desired_currency_code)
        self.sprint(f"    Cache key: '{cache_key}'")
        cache_entry_db = self.__cache_dao.get(cache_key)
        if cache_entry_db:
            cache_entry = ToolsCache.model_validate(cache_entry_db)
            if not cache_entry.is_expired():
                self.sprint(f"Cache hit for direct conversion and key '{cache_key}'")
                return float(cache_entry.value)
            self.sprint(f"Cache expired for direct conversion and key '{cache_key}'")
        self.sprint(f"Cache miss for direct conversion and key '{cache_key}'")

        # now let's check for the inverse conversion rate
        self.sprint(f"Fetching cached inverse rate for {base_currency_code}/{desired_currency_code}")
        cache_key = self.__cache_key_of(desired_currency_code, base_currency_code)
        self.sprint(f"    Cache key: '{cache_key}'")
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

        if base_currency_code == desired_currency_code:
            return 1.0

        cached_rate = self.__get_cached_rate_of_one(base_currency_code, desired_currency_code)
        if cached_rate:
            return cached_rate

        rate: float
        api_url = f"https://pro-api.coinmarketcap.com/{CRYPTO_CURRENCY_EXCHANGE.id.replace(".", "/")}"
        cmc_token = self.__token_resolver.require_access_token_for_tool(CRYPTO_CURRENCY_EXCHANGE).get_secret_value()
        headers = {"Accept": "application/json", "X-CMC_PRO_API_KEY": cmc_token}
        if base_currency_code != DEFAULT_FIAT and desired_currency_code != DEFAULT_FIAT:
            # due to API limitations, we must traverse both cryptos through USD
            params_base = {"symbol": base_currency_code, "convert": DEFAULT_FIAT}
            sleep(RATE_LIMIT_DELAY_S)
            fetcher_base = WebFetcher(
                api_url,
                self.__cache_dao,
                headers = headers,
                params = params_base,
                cache_ttl_json = CACHE_TTL,
            )
            response_base = fetcher_base.fetch_json() or {}

            params_desired = {"symbol": desired_currency_code, "convert": DEFAULT_FIAT}
            sleep(RATE_LIMIT_DELAY_S)
            fetcher_desired = WebFetcher(
                api_url,
                self.__cache_dao,
                headers = headers,
                params = params_desired,
                cache_ttl_json = CACHE_TTL,
            )
            response_desired = fetcher_desired.fetch_json() or {}

            base_rate = float(response_base["data"][base_currency_code]["quote"][DEFAULT_FIAT]["price"])
            desired_rate = float(response_desired["data"][desired_currency_code]["quote"][DEFAULT_FIAT]["price"])
            rate = base_rate / desired_rate
        else:
            # one of the currencies is USD, we can fetch the rate directly
            symbol = desired_currency_code if base_currency_code == DEFAULT_FIAT else base_currency_code
            params = {"symbol": symbol, "convert": DEFAULT_FIAT}
            sleep(RATE_LIMIT_DELAY_S)
            fetcher = WebFetcher(
                api_url,
                self.__cache_dao,
                headers = headers,
                params = params,
                cache_ttl_json = CACHE_TTL,
            )
            response = fetcher.fetch_json() or {}

            rate = float(response["data"][symbol]["quote"][DEFAULT_FIAT]["price"])
            if base_currency_code == DEFAULT_FIAT:
                rate = 1 / rate
        if rate:
            self.__save_rate_to_cache(base_currency_code, desired_currency_code, rate)
            return rate
        raise ValueError(f"No rate found for {base_currency_code}/{desired_currency_code}")

    def get_fiat_conversion_rate(self, base_currency_code: str, desired_currency_code: str) -> float:
        self.sprint(f"Fetching fiat conversion rate {base_currency_code}/{desired_currency_code}")
        if base_currency_code not in SUPPORTED_FIAT:
            raise ValueError(f"Unsupported currency: {base_currency_code}")
        if desired_currency_code not in SUPPORTED_FIAT:
            raise ValueError(f"Unsupported currency: {desired_currency_code}")

        if base_currency_code == desired_currency_code:
            return 1.0
        cached_rate = self.__get_cached_rate_of_one(base_currency_code, desired_currency_code)
        if cached_rate:
            return cached_rate

        sleep(RATE_LIMIT_DELAY_S)
        api_url = f"https://{FIAT_CURRENCY_EXCHANGE.id}/currency/convert"
        params = {"format": "json", "from": base_currency_code, "to": desired_currency_code, "amount": "1.0"}
        rapid_api_token = self.__token_resolver.require_access_token_for_tool(FIAT_CURRENCY_EXCHANGE).get_secret_value()
        headers = {"X-RapidAPI-Key": rapid_api_token, "X-RapidAPI-Host": FIAT_CURRENCY_EXCHANGE.id}
        fetcher = WebFetcher(
            api_url,
            self.__cache_dao,
            headers = headers,
            params = params,
            cache_ttl_json = CACHE_TTL,
        )
        response = fetcher.fetch_json() or {}

        rate = float(response["rates"][desired_currency_code]["rate_for_amount"])
        if rate:
            self.__save_rate_to_cache(base_currency_code, desired_currency_code, rate)
            return rate
        raise ValueError(
            f"Invalid rate: {rate}; API: {FIAT_CURRENCY_EXCHANGE.id}; response data: {json.dumps(response)}",
        )
