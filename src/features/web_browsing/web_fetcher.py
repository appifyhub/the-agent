import json
import platform
import time
from datetime import timedelta, datetime

import requests
from requests.exceptions import RequestException, Timeout

from db.crud.tools_cache import ToolsCacheCRUD
from db.schema.tools_cache import ToolsCache, ToolsCacheSave
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

PLATFORM = f"{platform.python_implementation()}/{platform.python_version()}"
USER_AGENT = f"Mozilla/5.0 (compatible; TheAgent/1.0; {PLATFORM})"
HEADERS = {"User-Agent": USER_AGENT}
CACHE_PREFIX = "web-fetcher"
CACHE_TTL_HTML = timedelta(weeks = 3)
CACHE_TTL_JSON = timedelta(minutes = 5)


class WebFetcher(SafePrinterMixin):
    url: str
    html: str | None
    json: dict | None
    __cache_dao: ToolsCacheCRUD
    __cache_key: str

    def __init__(
        self,
        url: str,
        cache_dao: ToolsCacheCRUD,
        auto_fetch_html: bool = False,
        auto_fetch_json: bool = False,
    ):
        super().__init__(config.verbose)
        self.url = url
        self.html = None
        self.json = None
        self.__cache_dao = cache_dao
        self.__cache_key = cache_dao.create_key(CACHE_PREFIX, url)
        if auto_fetch_html:
            self.fetch_html()
        if auto_fetch_json:
            self.fetch_json()

    def fetch_html(self) -> str | None:
        self.html = None  # reset value

        cache_entry_db = self.__cache_dao.get(self.__cache_key)
        if cache_entry_db:
            cache_entry = ToolsCache.model_validate(cache_entry_db)
            if not cache_entry.is_expired():
                self.sprint(f"Cache hit for '{self.__cache_key}'")
                self.html = cache_entry.value
                return self.html
            self.sprint(f"Cache expired for '{self.__cache_key}'")
        self.sprint(f"Cache miss for '{self.__cache_key}'")

        attempts = 0
        for _ in range(config.web_retries):
            try:
                response = requests.get(self.url, headers = HEADERS, timeout = config.web_timeout_s)
                response.raise_for_status()
                self.html = response.text
                self.__cache_dao.save(
                    ToolsCacheSave(
                        key = self.__cache_key,
                        value = self.html,
                        expires_at = datetime.now() + CACHE_TTL_HTML,
                    )
                )
                break
            except (RequestException, Timeout) as e:
                attempts += 1
                attempts_left = config.web_retries - attempts + 1
                self.sprint(f"Error fetching HTML content: {e}. Retries left: {attempts_left}")
                time.sleep(config.web_retry_delay_s)
        return self.html

    def fetch_json(self) -> dict | None:
        self.json = None  # reset value

        cache_entry_db = self.__cache_dao.get(self.__cache_key)
        if cache_entry_db:
            cache_entry = ToolsCache.model_validate(cache_entry_db)
            if not cache_entry.is_expired():
                self.sprint(f"Cache hit for '{self.__cache_key}'")
                self.json = json.loads(cache_entry.value)
                return self.json
            self.sprint(f"Cache expired for '{self.__cache_key}'")
        self.sprint(f"Cache miss for '{self.__cache_key}'")

        attempts = 0
        for _ in range(config.web_retries):
            try:
                response = requests.get(self.url, headers = HEADERS, timeout = config.web_timeout_s)
                response.raise_for_status()
                self.json = response.json()
                self.__cache_dao.save(
                    ToolsCacheSave(
                        key = self.__cache_key,
                        value = json.dumps(self.json),
                        expires_at = datetime.now() + CACHE_TTL_JSON,
                    )
                )
                break
            except (RequestException, Timeout) as e:
                attempts += 1
                attempts_left = config.web_retries - attempts + 1
                self.sprint(f"Error fetching JSON content: {e}. Retries left: {attempts_left}")
                time.sleep(config.web_retry_delay_s)
        return self.json
