import json
import platform
import time
from datetime import datetime, timedelta
from typing import Any

import requests
from requests.exceptions import RequestException, Timeout

from db.schema.tools_cache import ToolsCache, ToolsCacheSave
from di.di import DI
from features.external_tools.tool_choice_resolver import ConfiguredTool
from features.web_browsing.twitter_status_fetcher import TwitterStatusFetcher
from features.web_browsing.twitter_utils import resolve_tweet_id
from features.web_browsing.uri_cleanup import simplify_url
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

PLATFORM = f"{platform.python_implementation()}/{platform.python_version()}"
USER_AGENT = f"Mozilla/5.0 (compatible; TheAgent/1.0; {PLATFORM})"
DEFAULT_HEADERS = {"User-Agent": USER_AGENT}
CACHE_PREFIX = "web-fetcher"
DEFAULT_CACHE_TTL_HTML = timedelta(weeks = 3)
DEFAULT_CACHE_TTL_JSON = timedelta(minutes = 5)


class WebFetcher(SafePrinterMixin):
    url: str
    html: str | None
    json: dict | None
    __tweet_id: str | None
    __cache_key: str
    __headers: dict[str, str]
    __params: dict[str, Any]
    __cache_ttl_html: timedelta
    __cache_ttl_json: timedelta
    __tweet_fetcher: TwitterStatusFetcher | None
    __di: DI

    def __init__(
        self,
        url: str,
        di: DI,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        cache_ttl_html: timedelta | None = None,
        cache_ttl_json: timedelta | None = None,
        auto_fetch_html: bool = False,
        auto_fetch_json: bool = False,
    ):
        super().__init__(config.verbose)
        self.url = url
        self.__di = di
        self.html = None
        self.json = None
        self.__headers = {**DEFAULT_HEADERS, **(headers or {})}
        self.__params = params or {}
        self.__cache_key = self.__generate_cache_key()
        self.__cache_ttl_html = cache_ttl_html or DEFAULT_CACHE_TTL_HTML
        self.__cache_ttl_json = cache_ttl_json or DEFAULT_CACHE_TTL_JSON
        self.__tweet_id = resolve_tweet_id(self.url)
        if self.__tweet_id:
            self.sprint(f"Resolved tweet ID: {self.__tweet_id}")
            twitter_api_tool = di.tool_choice_resolver.require_tool(
                TwitterStatusFetcher.TWITTER_TOOL_TYPE,
                TwitterStatusFetcher.DEFAULT_TWITTER_TOOL,
            )
            vision_tool = di.tool_choice_resolver.require_tool(
                TwitterStatusFetcher.VISION_TOOL_TYPE,
                TwitterStatusFetcher.DEFAULT_VISION_TOOL,
            )
            # load the system tool for now (will be migrated away)
            twitter_enterprise_tool: ConfiguredTool = (
                TwitterStatusFetcher.DEFAULT_TWITTER_TOOL,
                config.rapid_api_twitter_token,
                TwitterStatusFetcher.TWITTER_TOOL_TYPE,
            )
            self.__tweet_fetcher = di.twitter_status_fetcher(
                self.__tweet_id, twitter_api_tool, vision_tool, twitter_enterprise_tool,
            )
        else:
            self.__tweet_fetcher = None
        if auto_fetch_html:
            self.fetch_html()
        if auto_fetch_json:
            self.fetch_json()

    def __generate_cache_key(self) -> str:
        headers_str = json.dumps(self.__headers, sort_keys = True)
        params_str = json.dumps(self.__params, sort_keys = True)
        key_components = f"{simplify_url(self.url)}|{headers_str}|{params_str}"
        return self.__di.tools_cache_crud.create_key(CACHE_PREFIX, key_components)

    def fetch_html(self) -> str | None:
        self.html = None  # reset value

        cache_entry_db = self.__di.tools_cache_crud.get(self.__cache_key)
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
                if self.__tweet_fetcher:
                    response_text = self.__tweet_fetcher.execute()
                    self.html = f"<html><body>\n<p>\n{response_text}\n</p>\n</body></html>"
                else:
                    # run a standard request for a web page
                    response = requests.get(
                        self.url,
                        headers = self.__headers,
                        params = self.__params,
                        timeout = config.web_timeout_s,
                    )
                    response.raise_for_status()
                    # we need to check for binary content before caching
                    content_bytes = response.content
                    try:
                        content_text = content_bytes.decode(response.encoding or "utf-8")
                    except Exception:
                        self.sprint(f"Failed to decode content from {self.url}")
                        content_text = None
                    if b"\x00" in content_bytes or content_text is None:
                        self.sprint(f"Not caching binary or invalid content from {self.url}")
                        self.html = None
                        break
                    self.html = content_text
                self.__di.tools_cache_crud.save(
                    ToolsCacheSave(
                        key = self.__cache_key,
                        value = self.html or "",
                        expires_at = datetime.now() + self.__cache_ttl_html,
                    ),
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

        cache_entry_db = self.__di.tools_cache_crud.get(self.__cache_key)
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
                if self.__tweet_fetcher:
                    response_text = self.__tweet_fetcher.execute()
                    self.json = {"content": response_text}
                else:
                    response = requests.get(
                        self.url,
                        headers = self.__headers,
                        params = self.__params,
                        timeout = config.web_timeout_s,
                    )
                    response.raise_for_status()
                    self.json = response.json()
                self.__di.tools_cache_crud.save(
                    ToolsCacheSave(
                        key = self.__cache_key,
                        value = json.dumps(self.json),
                        expires_at = datetime.now() + self.__cache_ttl_json,
                    ),
                )
                break
            except (RequestException, Timeout) as e:
                attempts += 1
                attempts_left = config.web_retries - attempts + 1
                self.sprint(f"Error fetching JSON content: {e}. Retries left: {attempts_left}")
                time.sleep(config.web_retry_delay_s)
        return self.json
